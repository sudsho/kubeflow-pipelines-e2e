"""feature schema + light validation.

pipeline components import FEATURE_COLS and TARGET so the whole thing stays in one place.
"""
from typing import List

FEATURE_COLS: List[str] = [
    "units_lag_1",
    "units_lag_7",
    "units_lag_14",
    "units_lag_28",
    "units_ma_7",
    "units_ma_28",
    "avg_price",
    "promo_touches",
    "dow",
    "week_of_year",
    "month_of_year",
    "is_weekend",
]

TARGET = "y_units_h7"


def validate(df):
    missing = [c for c in FEATURE_COLS + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError("missing columns in features frame: %s" % missing)
    if df[TARGET].isna().any():
        raise ValueError("target column has NaN rows")
    return True
