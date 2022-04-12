"""kfp component: read raw features parquet, add label column, split into train/holdout."""
from kfp.v2.dsl import component, Input, Output, Dataset


@component(
    base_image="python:3.9",
    packages_to_install=["pandas==1.4.2", "pyarrow==7.0.0"],
)
def build_training_frame(
    raw_features: Input[Dataset],
    horizon_days: int,
    holdout_days: int,
    train_frame: Output[Dataset],
    holdout_frame: Output[Dataset],
):
    import pandas as pd

    df = pd.read_parquet(raw_features.path)
    df["ds"] = pd.to_datetime(df["ds"])

    df = df.sort_values(["store_id", "sku_id", "ds"])
    df["y_units_h7"] = (
        df.groupby(["store_id", "sku_id"])["units"]
        .transform(lambda s: s.shift(-1).rolling(horizon_days).sum())
    )
    df = df.dropna(subset=["y_units_h7"])

    cutoff = df["ds"].max() - pd.Timedelta(days=holdout_days)
    tr = df[df["ds"] <= cutoff]
    ho = df[df["ds"] > cutoff]

    tr.to_parquet(train_frame.path, index=False)
    ho.to_parquet(holdout_frame.path, index=False)
