# kubeflow-pipelines-e2e

End-to-end retail demand forecasting pipeline on Kubeflow Pipelines. Runs on GKE
Autopilot, uses GCS as the artifact store, and registers the trained model in Vertex
AI Model Registry. XGBoost is the production model; Prophet ships alongside as a
per-SKU baseline so a bad week of features never silently hurts revenue.

## the problem

For a big-box retailer with a few thousand stores and tens of thousands of active SKUs,
the weekly replenishment plan hinges on a horizon-7 forecast of unit demand per store
per SKU. The forecast has to:

- retrain nightly from fresh POS data in BigQuery
- respect seasonality (weekly + yearly + holidays) and promo lift
- have a hard quality gate before it can affect ordering (WMAPE > 0.35 blocks release)
- version cleanly in a model registry so we can roll back without a rebuild

## architecture

```
    BigQuery (retail_raw.pos_daily)
              |
              | features.sql + label.sql
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

Full architecture writeup and DAG rationale in [`docs/architecture.md`](docs/architecture.md).

## quick start

Local sanity check (compiles the pipeline, runs unit tests, no cloud calls):

```bash
make setup
make test
make compile
```

Deploy the KFP standalone stack on a fresh GKE cluster and submit a run:

```bash
cd terraform && terraform init && terraform apply \
  -var project=$GCP_PROJECT \
  -var artifact_bucket=$GCS_BUCKET
cd ..
gcloud container clusters get-credentials $GKE_CLUSTER --region $GCP_REGION
bash k8s/install_kfp.sh                            # see k8s/README.md
python pipelines/compile.py --out dist/spec.json
python pipelines/submit.py --project $GCP_PROJECT --package dist/spec.json
```

Serve the last-registered model locally:

```bash
gsutil cp gs://$GCS_BUCKET/models/demand_forecast_xgb/model.json local-models/xgb.json
docker compose up serving
curl -s localhost:8080/healthz | jq
```

## repo layout

```
pipelines/
  demand_forecast.py         KFP v1 pipeline definition
  compile.py                 compile to IR JSON
  submit.py                  submit to a KFP endpoint
  components/                one @dsl.component per step
sql/
  features.sql               daily feature build (BigQuery)
  label.sql                  horizon-7 label
src/
  features/                  schema + local feature build helper
  train/                     xgboost + prophet trainers (CLI-callable)
  eval/                      metrics + report + holdout split
  serving/                   FastAPI serving app + predictor
k8s/                         SA + RBAC + install notes
terraform/                   GKE, GCS, IAM (workload identity)
docs/                        architecture, gke setup, kfp notes, vertex registry
notebooks/                   EDA + pipeline walkthrough
tests/                       unit + compile smoke
```

## results (dev cluster, 30 stores x 5000 SKUs, 90 days holdout window)

| model               | WMAPE  | MAE   | RMSE  |
|---------------------|--------|-------|-------|
| Prophet per-SKU     | 0.412  | 8.6   | 17.4  |
| XGBoost + lags      | 0.284  | 5.9   | 12.1  |

The XGBoost head passes the 0.35 gate and is what gets registered.

## era notes

Written in April 2022 against `kfp==1.8.13`. KFP v2 was still in beta then; we compile
with `kfp.v2.compiler.Compiler` (which produces the JSON PipelineSpec IR) and submit to
the KFP standalone v1 API server. If you are picking this up later, see
[`docs/kfp_v1_notes.md`](docs/kfp_v1_notes.md) for the client-server pinning that keeps
this working.

## license

MIT. See `LICENSE`.
