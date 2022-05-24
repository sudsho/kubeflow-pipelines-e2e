# architecture

## overview

Sketch of a demand forecast pipeline for a store x SKU grid, structured as a
Kubeflow Pipelines job. BigQuery is the intended source of POS data. GCS is the
pipeline artifact store. Vertex Model Registry is where a passing model would be
registered for downstream serving. This document describes the intended shape;
the pipeline has not been run end to end.

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
2. `sql/features.sql` builds a daily feature table with lag / rolling / calendar
   features and writes to `retail_features.features_daily`.
3. KFP `read_bq_features` executes the features query and exports parquet to the
   pipeline artifact store on GCS.
4. `build_training_frame` builds the label locally on the parquet and splits
   train / holdout by date. The label logic in this repo is a placeholder and is
   not a validated forward-looking horizon-7 target; treat it as a scaffold.
5. `train_xgb` fits an xgboost regressor; `prophet_op` fits a group-wise Prophet
   baseline.
6. `evaluate` computes WMAPE on the holdout for xgboost and returns a `passed`
   flag. The Prophet arm of the evaluate step is not exercised end to end (see
   the note in `pipelines/components/evaluate_op.py`).
7. If `passed`, `register_in_vertex` uploads the booster to GCS and pushes a new
   version under a stable display_name in Vertex Model Registry.

## why this shape

- **BigQuery for features**: it is where the raw data lives, and SQL is the
  shortest path to lag / rolling / calendar features at scale.
- **KFP v1 (kfp==1.8.13)**: the standalone install on GKE was chosen for the era
  because it did not require managed Vertex Pipelines and let pods run under a
  workload-identity-bound service account.
- **XGBoost + Prophet baseline**: XGBoost with lag features is a common retail
  workhorse; a Prophet baseline is intended as a sanity check for slow-moving
  SKUs where lag features are sparse.
- **Vertex Model Registry**: downstream serving reads the latest version by
  display_name, decoupling training from serving.

## caveats

- No scheduler is configured in this repo; there is no CronJob, Cloud Scheduler
  resource, or KFP recurring-run definition. `submit.py` performs a single
  one-off run.
- The Prophet component fits one model per (store, sku) inside a serial Python
  loop, and no per-component CPU / memory requests are set. Neither has been
  tuned or measured on a real grid; treat scale numbers you may see in old
  notes as untested.
