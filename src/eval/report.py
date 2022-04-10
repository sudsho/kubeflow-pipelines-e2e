"""eval report that compares xgb vs prophet on the holdout window and writes html + json."""
import argparse
import json
import logging
import pathlib

import pandas as pd
import xgboost as xgb

from src.eval.metrics import report as compute_report
from src.features.schema import FEATURE_COLS, TARGET

log = logging.getLogger(__name__)


HTML_TMPL = """<html><head><meta charset="utf-8"><title>demand forecast eval</title></head>
<body style="font-family:sans-serif;max-width:900px;margin:24px auto;">
<h2>demand forecast eval</h2>
<p>holdout window: last {holdout} days.</p>
<h3>xgb</h3><pre>{xgb}</pre>
<h3>prophet baseline</h3><pre>{proph}</pre>
</body></html>
"""


def eval_xgb(model_path, holdout_df):
    m = xgb.XGBRegressor()
    m.load_model(model_path)
    yhat = m.predict(holdout_df[FEATURE_COLS])
    return compute_report(holdout_df[TARGET], yhat)


def eval_prophet(prophet_fc, holdout_df):
    merged = holdout_df.merge(prophet_fc, on=["store_id", "sku_id", "ds"], how="inner")
    if merged.empty:
        log.warning("prophet forecast has no overlap with holdout; skipping")
        return {}
    return compute_report(merged[TARGET], merged["yhat"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--xgb-model", required=True)
    ap.add_argument("--prophet-forecast", required=True)
    ap.add_argument("--holdout-days", type=int, default=28)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-html", required=True)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)
    df = pd.read_parquet(args.features)
    cutoff = df["ds"].max() - pd.Timedelta(days=args.holdout_days)
    ho = df[df["ds"] > cutoff]

    xgb_metrics = eval_xgb(args.xgb_model, ho)
    proph_metrics = eval_prophet(pd.read_parquet(args.prophet_forecast), ho)

    result = {"xgb": xgb_metrics, "prophet": proph_metrics, "holdout_days": args.holdout_days}
    pathlib.Path(args.out_json).write_text(json.dumps(result, indent=2))
    pathlib.Path(args.out_html).write_text(HTML_TMPL.format(
        holdout=args.holdout_days,
        xgb=json.dumps(xgb_metrics, indent=2),
        proph=json.dumps(proph_metrics, indent=2),
    ))
    log.info("wrote eval report to %s and %s", args.out_json, args.out_html)


if __name__ == "__main__":
    main()
