"""kfp component: upload the xgb model to gcs and register a new version in vertex model registry."""
from kfp.dsl import component, Input, Model


@component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-aiplatform==1.11.0",
        "google-cloud-storage==2.3.0",
    ],
)
def register_in_vertex(
    project: str,
    region: str,
    gcs_staging: str,
    display_name: str,
    xgb_model: Input[Model],
):
    """upload booster to gcs then register/version it in vertex model registry.

    Args:
        project: gcp project id.
        region: vertex region, e.g. us-central1.
        gcs_staging: gs://bucket/prefix where the booster is uploaded.
        display_name: model display name (versions share a display name).
        xgb_model: input model artifact from the training step.
    """
    import os
    import pathlib

    local = xgb_model.path + ".json"
    assert pathlib.Path(local).exists(), local

    if os.environ.get("DEMAND_FORECAST_SYNTHETIC") == "1":
        # offline path: skip the GCS upload + Vertex Model Registry call so the
        # gated register step can be exercised on CPU with no credentials.
        print(f"[offline] skipping vertex register; model staged at {local}")
        return

    from google.cloud import aiplatform, storage

    assert gcs_staging.startswith("gs://"), gcs_staging
    without = gcs_staging[len("gs://"):]
    bucket_name, prefix = without.split("/", 1) if "/" in without else (without, "")
    blob_name = f"{prefix.rstrip('/')}/{display_name}/model.json"

    storage_client = storage.Client(project=project)
    storage_client.bucket(bucket_name).blob(blob_name).upload_from_filename(local)
    artifact_uri = f"gs://{bucket_name}/{prefix.rstrip('/')}/{display_name}"

    aiplatform.init(project=project, location=region, staging_bucket=gcs_staging)

    existing = aiplatform.Model.list(filter=f'display_name="{display_name}"')
    parent = existing[0].resource_name if existing else None

    aiplatform.Model.upload(
        display_name=display_name,
        artifact_uri=artifact_uri,
        serving_container_image_uri=(
            "us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"
        ),
        parent_model=parent,
        sync=True,
    )
