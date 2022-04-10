"""holdout split helper. keeps split logic centralised so training and eval agree."""
import pandas as pd


def build_holdout(df, holdout_days=28):
    max_ds = df["ds"].max()
    cutoff = max_ds - pd.Timedelta(days=holdout_days)
    train_df = df[df["ds"] <= cutoff].copy()
    holdout_df = df[df["ds"] > cutoff].copy()
    return train_df, holdout_df, cutoff
