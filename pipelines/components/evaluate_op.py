"""kfp component: evaluate xgb and prophet on the holdout, emit metrics json + gating decision."""
from typing import NamedTuple

from kfp.v2.dsl import component, Input, Output, Dataset, Model, Metrics


@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas==1.4.2",
        "pyarrow==7.0.0",
        "xgboost==1.5.2",
        "numpy==1.22.3",
    ],
)
def evaluate(
    holdout_frame: Input[Dataset],
    xgb_model: Input[Model],
    prophet_forecast: Input[Dataset],
    metrics: Output[Metrics],
    wmape_threshold: float = 0.35,
) -> NamedTuple("Outputs", [("passed", bool), ("wmape", float)]):
    import json
    import numpy as np
    import pandas as pd
    import xgboost as xgb

    feat_cols = [
        "units_lag_1", "units_lag_7", "units_lag_14", "units_lag_28",
        "units_ma_7", "units_ma_28", "avg_price", "promo_touches",
        "dow", "week_of_year", "month_of_year", "is_weekend",
    ]
    target = "y_units_h7"

    ho = pd.read_parquet(holdout_frame.path)
    prox = pd.read_parquet(prophet_forecast.path)

    m = xgb.XGBRegressor()
    m.load_model(xgb_model.path + ".json")
    yhat_xgb = m.predict(ho[feat_cols])
    denom = float(np.sum(np.abs(ho[target])))

    def _wmape(y, yhat):
        return float(np.sum(np.abs(np.asarray(y) - np.asarray(yhat))) / max(denom, 1e-9))

    wmape_xgb = _wmape(ho[target], yhat_xgb)

    merged = ho.merge(prox, on=["store_id", "sku_id", "ds"], how="inner")
    wmape_proph = _wmape(merged[target], merged["yhat"]) if len(merged) else float("nan")

    metrics.log_metric("wmape_xgb", wmape_xgb)
    metrics.log_metric("wmape_prophet", wmape_proph)
    metrics.log_metric("holdout_rows", int(len(ho)))

    passed = wmape_xgb <= wmape_threshold
    from collections import namedtuple
    Out = namedtuple("Outputs", ["passed", "wmape"])
    return Out(passed=passed, wmape=wmape_xgb)
