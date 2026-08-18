"""synthetic demand-forecasting dataset generator (offline, no cloud).

Produces a frame with the same schema that ``sql/features.sql`` emits from
BigQuery, so the feature / train / evaluate components can run standalone on
CPU with no BigQuery, no GCS, and no credentials.

The raw daily series for each (store, sku) is trend + weekly seasonality +
yearly seasonality + promo bumps + noise, floored at zero. The lag / rolling /
calendar features are then computed in pandas to mirror the window functions in
``sql/features.sql``.
"""
from typing import List
import numpy as np
import pandas as pd

# columns the downstream components expect on the raw features frame.
RAW_COLS: List[str] = [
    "store_id", "sku_id", "ds", "units", "avg_price", "promo_touches",
    "units_lag_1", "units_lag_7", "units_lag_14", "units_lag_28",
    "units_ma_7", "units_ma_28",
    "dow", "week_of_year", "month_of_year", "is_weekend",
]


def _daily_series(rng: np.random.Generator, n_days: int, base: float) -> pd.DataFrame:
    """one (store, sku) daily series: trend + weekly + yearly + promo + noise."""
    t = np.arange(n_days)
    trend = base + 0.02 * base * (t / 30.0)
    weekly = 0.25 * base * np.sin(2 * np.pi * t / 7.0)
    yearly = 0.35 * base * np.sin(2 * np.pi * t / 365.0)
    promo_flag = (rng.random(n_days) < 0.08).astype(int)
    promo_lift = promo_flag * 0.6 * base
    noise = rng.normal(0.0, 0.12 * base, size=n_days)

    units = np.clip(trend + weekly + yearly + promo_lift + noise, 0.0, None)
    units = np.round(units).astype(float)

    price = 10.0 + 0.5 * base + rng.normal(0.0, 0.4, size=n_days)
    price = np.where(promo_flag == 1, price * 0.85, price)
    return pd.DataFrame({
        "units": units,
        "avg_price": np.round(price, 2),
        "promo_touches": promo_flag,
    })


def generate_raw_features(
    n_stores: int = 3,
    n_skus: int = 4,
    n_days: int = 540,
    seed: int = 42,
) -> pd.DataFrame:
    """generate a raw features frame matching ``sql/features.sql`` output.

    Args:
        n_stores: number of stores.
        n_skus: number of skus per store.
        n_days: length of the daily history per (store, sku).
        seed: rng seed for reproducibility.

    Returns:
        DataFrame with :data:`RAW_COLS`, one row per (store, sku, day) with the
        first 28 warmup days dropped so ``units_lag_28`` is always present.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n_days, freq="D")

    frames = []
    for s in range(n_stores):
        for k in range(n_skus):
            base = float(rng.integers(20, 120))
            g = _daily_series(rng, n_days, base)
            g["ds"] = dates
            g["store_id"] = f"S{s:02d}"
            g["sku_id"] = f"K{k:03d}"
            frames.append(g)

    df = pd.concat(frames, ignore_index=True)
    return _engineer(df)


def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    """add lag / rolling / calendar features, mirroring sql/features.sql."""
    df = df.sort_values(["store_id", "sku_id", "ds"]).reset_index(drop=True)
    grp = df.groupby(["store_id", "sku_id"])["units"]

    for lag in (1, 7, 14, 28):
        df[f"units_lag_{lag}"] = grp.shift(lag)

    # rolling means over the trailing window, excluding the current day
    # (ROWS BETWEEN N PRECEDING AND 1 PRECEDING in the SQL).
    df["units_ma_7"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    df["units_ma_28"] = grp.transform(lambda s: s.shift(1).rolling(28, min_periods=1).mean())

    ds = df["ds"].dt
    # DAYOFWEEK in BigQuery is 1..7 with Sunday=1; replicate that convention.
    df["dow"] = (ds.dayofweek + 1) % 7 + 1
    df["week_of_year"] = ds.isocalendar().week.astype(int)
    df["month_of_year"] = ds.month
    df["is_weekend"] = df["dow"].isin([1, 7]).astype(int)

    df = df.dropna(subset=["units_lag_28"]).reset_index(drop=True)
    return df[RAW_COLS]
