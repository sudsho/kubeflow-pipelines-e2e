# kubeflow-pipelines-e2e

Retail demand forecasting pipeline on Kubeflow Pipelines (`kfp>=2.7`). GCS as the
artifact store, XGBoost as the primary model, Prophet included as a per-SKU
baseline, Vertex Model Registry as the gated sink. Designed for GKE, but the
pipeline compiles and its components run offline on CPU against a synthetic
demand dataset, so you can clone it and see real metrics with no cloud account.

The live path (BigQuery source, GCS artifacts, GKE execution, Vertex register)
still needs GCP setup and is not exercised here. Every cloud call is guarded
behind `DEMAND_FORECAST_SYNTHETIC=1` so compiling and the local run never touch
credentials.

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

## quick start (runs offline, no keys)

No GCP project, no API keys, no large downloads. Needs Python 3.9+ and CPU only.

```bash
pip install -r requirements.txt
python pipelines/run_local.py
```

This compiles the pipeline to `dist/demand_forecast.json`, generates a synthetic
demand dataset (seasonal + trend + noise), and runs the read, feature, XGBoost
train, and evaluate components locally by invoking each component's own function
body. Real verified output on this machine (CPU, kfp 2.7.0, xgboost 3.2.0):

```
==============================================================
STEP 1  compile pipeline
==============================================================
compiled package : dist/demand_forecast.json (33609 bytes)
pipeline name    : retail-demand-forecast
components (7)   : build-training-frame, condition-1, evaluate, read-bq-features, register-in-vertex, train-prophet-baseline, train-xgb
root dag tasks   : build-training-frame, condition-1, evaluate, read-bq-features, train-prophet-baseline, train-xgb
validation       : OK (spec parsed, components present)

==============================================================
STEP 2  run components locally on synthetic demand data
==============================================================
synthetic raw    : 6144 rows, 12 store-sku series
train / holdout  : 5724 / 336 rows
trained model    : ...\model.json (1673138 bytes)

==============================================================
HOLDOUT METRICS (xgboost, synthetic demand)
==============================================================
  MAE   : 20.005 units
  MAPE  : 2.46 %
  WMAPE : 2.55 %
  RMSE  : 30.381 units
  bias  : -0.84 %
  gate  : passed=True (wmape=0.0255 <= 0.35)

==============================================================
SMOKE OK
==============================================================
pipeline compiled and components ran offline on CPU. exit 0.
```

Unit tests (17 passing):

```bash
make test        # or: python -m pytest -q
```

Compile the pipeline package on its own:

```bash
make compile     # writes dist/demand_forecast.json
```

Submitting to a live KFP standalone cluster on GKE requires additional setup
that is not exercised here; see [`docs/kfp_v1_notes.md`](docs/kfp_v1_notes.md)
for the kfp 2.x port note and the v1 gotchas.

## repo layout

```
pipelines/
  demand_forecast.py         KFP pipeline definition
  compile.py                 compile entrypoint
  run_local.py               offline CPU smoke (compile + run components)
  submit.py                  submit entrypoint
  components/                one @dsl.component per step
sql/
  features.sql               daily feature build (BigQuery)
src/
  features/                  feature schema helpers + synthetic generator
  eval/                      metrics helpers (mae, rmse, wmape, mape, bias)
  serving/                   FastAPI serving app + predictor
k8s/                         SA + RBAC + install notes
terraform/                   GKE, GCS, IAM sketches
docs/                        architecture, gke setup, kfp notes, vertex registry
notebooks/                   EDA sketch
tests/                       unit tests for feature schema and metrics helpers
```

## results

The numbers above are from the offline CPU smoke on a synthetic demand dataset,
not a production benchmark. They exist to prove the feature, train, and evaluate
components actually run and produce real metrics end to end. On the synthetic
series the XGBoost model reaches roughly 2.5 percent WMAPE on the 336-row
holdout and clears the 0.35 WMAPE registration gate. The pipeline has not been
run against a live BigQuery source, and no production eval artifacts are
committed.

## license

MIT. See `LICENSE`.
