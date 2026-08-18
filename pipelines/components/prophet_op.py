"""kfp component: fit prophet baseline over each (store, sku), emit yhat parquet."""
from kfp.dsl import component, Input, Output, Dataset


@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas==1.4.2",
        "pyarrow==7.0.0",
        "prophet==1.0",
    ],
)
def train_prophet_baseline(
    raw_features: Input[Dataset],
    horizon_days: int,
    forecast: Output[Dataset],
):
    import pandas as pd
    from prophet import Prophet

    df = pd.read_parquet(raw_features.path)
    df["ds"] = pd.to_datetime(df["ds"])

    out_frames = []
    for (store, sku), g in df.groupby(["store_id", "sku_id"]):
        if len(g) < 180:
            continue
        gg = g.rename(columns={"units": "y"})[["ds", "y"]]
        m = Prophet(weekly_seasonality=True, yearly_seasonality=True)
        try:
            m.fit(gg)
        except Exception:
            continue
        future = m.make_future_dataframe(periods=horizon_days, freq="D", include_history=False)
        fc = m.predict(future)[["ds", "yhat"]]
        fc["store_id"] = store
        fc["sku_id"] = sku
        out_frames.append(fc)

    if out_frames:
        pd.concat(out_frames, ignore_index=True).to_parquet(forecast.path, index=False)
    else:
        pd.DataFrame(columns=["store_id", "sku_id", "ds", "yhat"]).to_parquet(forecast.path, index=False)
