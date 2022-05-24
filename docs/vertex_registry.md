# vertex model registry

Every passing model is intended to be registered under a single stable
`display_name` (`demand_forecast_xgb`). Each successful pipeline run creates a
new **version** under that model, incrementing the version counter
automatically.

## why display_name and not model_id

Downstream serving containers look up the model by `display_name` and pull the
latest version. This lets the serving container image stay immutable and lets
rollback happen at the registry (mark previous version as default) rather than
needing a new image push.

## upload code

The component `pipelines/components/register_vertex_op.py`:

1. Uploads the booster JSON to
   `gs://$GCS_BUCKET/models/demand_forecast_xgb/model.json`.
2. Calls `aiplatform.Model.upload(display_name=..., parent_model=..., artifact_uri=...)`.
3. If a model with the same display_name already exists, passes its resource
   name as `parent_model` so Vertex versions the new upload rather than creating
   a new stem.
4. Uses the public XGBoost serving container `xgboost-cpu.1-4` for a zero-effort
   Vertex-endpoint deploy path.

## reading the latest model in the serving container

```python
from google.cloud import aiplatform
aiplatform.init(project=PROJECT, location=REGION)
models = aiplatform.Model.list(filter=f'display_name="demand_forecast_xgb"')
latest = models[0]                       # sorted newest first
```

## endpoint deploy

A Vertex endpoint deploy path is not wired up in this repo. The FastAPI app
under `src/serving/` is a scaffold and has not been latency-benchmarked.
