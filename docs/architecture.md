# architecture

## overview

End-to-end weekly demand forecast for a store x SKU grid, running as a Kubeflow Pipelines
job on GKE. BigQuery is the source of truth for POS data. GCS is the pipeline artifact
store. Vertex Model Registry is where a passing model becomes available to downstream
serving containers.

## dag

```
    +-------------+     +-------------------+     +----------------+
    |  read_bq    | --> |  build_training   | --> |  train_xgb     |
    | features    |     |  frame            |     |  (n_est=600)   |
    +-------------+     +-------------------+     +----------------+
           |                       |                       |
           |                       v                       |
           |             +-----------------+               |
           +-----------> |  prophet        |               |
                         |  baseline       |               |
                         +-----------------+               |
                                    \                      /
                                     v                    v
                                +---------------------------+
                                |   evaluate (wmape gate)   |
                                +---------------------------+
                                             |
                                    passed == True
                                             |
                                             v
                                +---------------------------+
                                |  register in vertex       |
                                |  model registry           |
                                +---------------------------+
```

## data path

1. `retail_raw.pos_daily` (BigQuery) has one row per store x SKU x day.
2. `sql/features.sql` builds a daily feature table with lag / rolling / calendar features
   and writes to `retail_features.features_daily`.
3. `sql/label.sql` builds the horizon-7 label column.
4. KFP `read_bq_features` executes the features query and exports parquet to the pipeline
   artifact store on GCS.
5. `build_training_frame` computes the label locally on the parquet and splits train /
   holdout by date (last 28 days is holdout).
6. `train_xgb` fits an xgboost regressor; `prophet_op` fits a group-wise Prophet baseline.
7. `evaluate` computes WMAPE on the holdout for both and returns a `passed` flag.
8. If `passed`, `register_in_vertex` uploads the booster to GCS and pushes a new version
   under a stable display_name in Vertex Model Registry.

## why this shape

- **BigQuery for features**: it is where the raw data already lives, and SQL is the shortest
  path to lag / rolling / calendar features at scale.
- **KFP v1 (kfp==1.8.13)**: the standalone install on GKE is stable, does not require
  managed Vertex Pipelines, and lets us run pods with our own service account.
- **XGBoost + Prophet baseline**: XGBoost with lag features is the retail workhorse; a
  Prophet baseline keeps us honest, especially for slow-moving SKUs where lag features are
  sparse.
- **Vertex Model Registry**: downstream serving (batch + online) reads the latest passing
  version by display_name, decoupling training from serving.

## sla

- Pipeline runs nightly at 04:00 IST, wall-clock target 45 min for a 30-store x 5000-SKU
  grid.
- If WMAPE on holdout > 0.35, the pipeline stops before the register step and pages
  ml-ops on-call.
