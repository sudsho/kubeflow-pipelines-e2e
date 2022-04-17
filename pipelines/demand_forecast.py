"""kubeflow v1 pipeline: read_bq -> features -> train xgb + prophet -> evaluate -> register."""
from kfp.v2 import dsl

from pipelines.components.read_bq import read_bq_features
from pipelines.components.features_op import build_training_frame
from pipelines.components.train_xgb_op import train_xgb
from pipelines.components.prophet_op import train_prophet_baseline
from pipelines.components.evaluate_op import evaluate
from pipelines.components.register_vertex_op import register_in_vertex


@dsl.pipeline(
    name="retail-demand-forecast",
    description="daily retail demand forecast: BQ features + XGB + prophet baseline + vertex register",
    pipeline_root="gs://REPLACE_ME/kfp-root",
)
def demand_forecast_pipeline(
    project: str,
    region: str = "us-central1",
    sql_gcs_uri: str = "gs://REPLACE_ME/sql/features.sql",
    dest_table: str = "REPLACE_ME.retail_features.features_daily",
    gcs_staging: str = "gs://REPLACE_ME/models",
    horizon_days: int = 7,
    holdout_days: int = 28,
    n_estimators: int = 600,
    max_depth: int = 8,
    learning_rate: float = 0.04,
    wmape_threshold: float = 0.35,
    display_name: str = "demand_forecast_xgb",
):
    raw = read_bq_features(
        project=project,
        sql_gcs_uri=sql_gcs_uri,
        dest_table=dest_table,
    )

    frames = build_training_frame(
        raw_features=raw.outputs["features"],
        horizon_days=horizon_days,
        holdout_days=holdout_days,
    )

    xgb_step = train_xgb(
        train_frame=frames.outputs["train_frame"],
        holdout_frame=frames.outputs["holdout_frame"],
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
    )

    proph_step = train_prophet_baseline(
        raw_features=raw.outputs["features"],
        horizon_days=horizon_days,
    )

    eval_step = evaluate(
        holdout_frame=frames.outputs["holdout_frame"],
        xgb_model=xgb_step.outputs["model"],
        prophet_forecast=proph_step.outputs["forecast"],
        wmape_threshold=wmape_threshold,
    )

    with dsl.Condition(eval_step.outputs["passed"] == True, name="gate-on-wmape"):  # noqa: E712
        register_in_vertex(
            project=project,
            region=region,
            gcs_staging=gcs_staging,
            display_name=display_name,
            xgb_model=xgb_step.outputs["model"],
        )
