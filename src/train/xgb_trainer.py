"""xgboost regressor for horizon-7 unit demand.

reads a parquet features frame, splits by date (last 28 days = holdout), trains an
xgboost regressor, and writes the booster to the given output path.
"""
import argparse
import json
import logging
import pathlib

import pandas as pd
import xgboost as xgb

from src.features.schema import FEATURE_COLS, TARGET, validate

log = logging.getLogger(__name__)


DEFAULT_PARAMS = {
    "n_estimators": 400,
    "max_depth": 7,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "random_state": 42,
}


def time_split(df, holdout_days=28):
    max_ds = df["ds"].max()
    cutoff = max_ds - pd.Timedelta(days=holdout_days)
    tr = df[df["ds"] <= cutoff]
    ho = df[df["ds"] > cutoff]
    return tr, ho


def train(df, params):
    validate(df)
    tr, ho = time_split(df)
    log.info("train rows=%d holdout rows=%d", len(tr), len(ho))
    m = xgb.XGBRegressor(**params)
    m.fit(
        tr[FEATURE_COLS], tr[TARGET],
        eval_set=[(ho[FEATURE_COLS], ho[TARGET])],
        verbose=False,
    )
    return m, tr, ho


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, help="parquet path")
    ap.add_argument("--model-out", required=True)
    ap.add_argument("--params", default=None, help="optional params json path")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)
    df = pd.read_parquet(args.features)
    params = DEFAULT_PARAMS.copy()
    if args.params:
        params.update(json.loads(pathlib.Path(args.params).read_text()))

    m, _, _ = train(df, params)
    pathlib.Path(args.model_out).parent.mkdir(parents=True, exist_ok=True)
    m.save_model(args.model_out)
    log.info("saved xgb model to %s", args.model_out)


if __name__ == "__main__":
    main()
