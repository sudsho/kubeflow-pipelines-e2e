"""prophet baseline for demand forecasting.

fits one prophet per (store_id, sku_id) group, forecasts horizon days ahead,
returns a long frame of yhat values. used as a sanity baseline for xgboost.
"""
import argparse
import logging
import pathlib

import pandas as pd
from prophet import Prophet

log = logging.getLogger(__name__)


def fit_group(g, horizon):
    m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    m.add_country_holidays(country_name="US")
    m.fit(g[["ds", "y"]])
    future = m.make_future_dataframe(periods=horizon, freq="D", include_history=False)
    fc = m.predict(future)
    fc["store_id"] = g["store_id"].iloc[0]
    fc["sku_id"] = g["sku_id"].iloc[0]
    return fc[["store_id", "sku_id", "ds", "yhat", "yhat_lower", "yhat_upper"]]


def run(df, horizon=7, min_history=180):
    out = []
    for (store, sku), g in df.groupby(["store_id", "sku_id"]):
        if len(g) < min_history:
            continue
        gg = g.rename(columns={"units": "y"})[["store_id", "sku_id", "ds", "y"]]
        try:
            out.append(fit_group(gg, horizon))
        except Exception as e:  # noqa: BLE001
            log.warning("prophet failed on store=%s sku=%s: %s", store, sku, e)
    if not out:
        return pd.DataFrame(columns=["store_id", "sku_id", "ds", "yhat"])
    return pd.concat(out, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--horizon", type=int, default=7)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)
    df = pd.read_parquet(args.features)
    fc = run(df, horizon=args.horizon)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fc.to_parquet(args.out, index=False)
    log.info("prophet forecast rows=%d -> %s", len(fc), args.out)


if __name__ == "__main__":
    main()
