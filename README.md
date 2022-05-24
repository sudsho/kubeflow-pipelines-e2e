# kubeflow-pipelines-e2e

Scaffold for a retail demand forecasting pipeline on Kubeflow Pipelines v1
(`kfp==1.8.13`). GCS as the artifact store, XGBoost as the primary model, Prophet
included as a per-SKU baseline. This repo is a code layout and DAG sketch; it has
not been run end to end against a live BigQuery source, and no benchmark numbers
are reported.

## problem sketch

Weekly replenishment for a store x SKU grid needs a short-horizon forecast of
unit demand. The pipeline in this repo aims at:

- reading POS features from BigQuery
- fitting XGBoost with lag / rolling / calendar features
- fitting a Prophet per (store, sku) group as a sanity baseline
- gating registration on a WMAPE threshold before uploading to Vertex Model
  Registry

## architecture

```
    BigQuery (retail_raw.pos_daily)
              |
              | features.sql
              v
    +---------------------+
    |  read_bq_features   |    (KFP component)
    +---------------------+
              |
              v
    +---------------------+
    |  build_training     |
    |  frame (train/hold) |
    +---------------------+
        /              \
       v                v
+----------+     +---------------+
|  xgboost |     |  prophet      |
|  train   |     |  baseline     |
+----------+     +---------------+
       \              /
        v            v
    +---------------------+
    |  evaluate (WMAPE)   |
    +---------------------+
              |
       passed == true
              |
              v
    +---------------------+
    |  register in Vertex |
    |  Model Registry     |
    +---------------------+
              |
              v
    Serving container reads latest version by display_name
```

DAG rationale in [`docs/architecture.md`](docs/architecture.md).

## quick start

Install and run the unit tests:

```bash
make setup
make test
```

Compiling and submitting to a live KFP standalone cluster requires additional
setup that is not exercised here; see [`docs/kfp_v1_notes.md`](docs/kfp_v1_notes.md)
for the pinning notes and gotchas.

## repo layout

```
pipelines/
  demand_forecast.py         KFP pipeline definition
  compile.py                 compile entrypoint
  submit.py                  submit entrypoint
  components/                one @dsl.component per step
sql/
  features.sql               daily feature build (BigQuery)
src/
  features/                  feature schema helpers
  eval/                      metrics helpers
  serving/                   FastAPI serving app + predictor
k8s/                         SA + RBAC + install notes
terraform/                   GKE, GCS, IAM sketches
docs/                        architecture, gke setup, kfp notes, vertex registry
notebooks/                   EDA sketch
tests/                       unit tests for feature schema and metrics helpers
```

## results

No benchmark numbers are reported in this repo. The pipeline has not been run
end to end against a live source and no eval artifacts are committed.

## license

MIT. See `LICENSE`.
