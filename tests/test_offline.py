"""offline path: synthetic generator schema + component run on CPU (no cloud)."""
import os

import pandas as pd
import pytest

from src.features.synthetic import generate_raw_features, RAW_COLS
from src.features.schema import FEATURE_COLS, TARGET, validate


class _Artifact:
    def __init__(self, path):
        self.path = str(path)
        self.metadata = {}


class _Metrics(_Artifact):
    def __init__(self, path):
        super().__init__(path)
        self.values = {}

    def log_metric(self, key, value):
        self.values[key] = value


def test_synthetic_schema_and_no_nulls():
    df = generate_raw_features(n_stores=2, n_skus=2, n_days=220, seed=7)
    assert list(df.columns) == RAW_COLS
    assert df.isna().sum().sum() == 0
    assert df.groupby(["store_id", "sku_id"]).ngroups == 4
    # every feature column the trainer needs is present.
    for c in FEATURE_COLS:
        assert c in df.columns


def test_offline_component_pipeline(tmp_path, monkeypatch):
    """read -> features -> train -> evaluate, all local on synthetic data."""
    monkeypatch.setenv("DEMAND_FORECAST_SYNTHETIC", "1")
    from pipelines.components.read_bq import read_bq_features
    from pipelines.components.features_op import build_training_frame
    from pipelines.components.train_xgb_op import train_xgb
    from pipelines.components.evaluate_op import evaluate

    raw = _Artifact(tmp_path / "raw.parquet")
    train_frame = _Artifact(tmp_path / "train.parquet")
    holdout_frame = _Artifact(tmp_path / "holdout.parquet")
    model = _Artifact(tmp_path / "model")
    prophet = _Artifact(tmp_path / "prophet.parquet")
    metrics = _Metrics(tmp_path / "metrics.json")

    read_bq_features.python_func(
        project="offline", sql_gcs_uri="gs://x/y.sql",
        dest_table="a.b.c", features=raw,
    )
    assert validate(_labelled(raw.path)) is True

    build_training_frame.python_func(
        raw_features=raw, horizon_days=7, holdout_days=28,
        train_frame=train_frame, holdout_frame=holdout_frame,
    )
    assert len(pd.read_parquet(holdout_frame.path)) > 0

    train_xgb.python_func(
        train_frame=train_frame, holdout_frame=holdout_frame,
        n_estimators=60, max_depth=4, learning_rate=0.1, model=model,
    )
    assert os.path.exists(model.path + ".json")

    pd.DataFrame(columns=["store_id", "sku_id", "ds", "yhat"]).to_parquet(
        prophet.path, index=False)

    out = evaluate.python_func(
        holdout_frame=holdout_frame, xgb_model=model,
        prophet_forecast=prophet, metrics=metrics, wmape_threshold=0.9,
    )
    assert 0.0 <= out.wmape < 1.0
    assert out.passed is True
    assert "wmape_xgb" in metrics.values


def _labelled(raw_path):
    """recreate the label column so schema.validate can run on the raw frame."""
    df = pd.read_parquet(raw_path)
    df[TARGET] = (
        df.groupby(["store_id", "sku_id"])["units"]
        .transform(lambda s: s.shift(-1).rolling(7).sum())
    )
    return df.dropna(subset=[TARGET])
