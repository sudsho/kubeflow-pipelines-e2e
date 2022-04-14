"""kfp component: train xgboost on the training frame, emit a Model artifact."""
from kfp.v2.dsl import component, Input, Output, Dataset, Model


@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas==1.4.2",
        "pyarrow==7.0.0",
        "xgboost==1.5.2",
        "scikit-learn==1.0.2",
        "numpy==1.22.3",
    ],
)
def train_xgb(
    train_frame: Input[Dataset],
    holdout_frame: Input[Dataset],
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    model: Output[Model],
):
    import json
    import pandas as pd
    import xgboost as xgb

    feat_cols = [
        "units_lag_1", "units_lag_7", "units_lag_14", "units_lag_28",
        "units_ma_7", "units_ma_28", "avg_price", "promo_touches",
        "dow", "week_of_year", "month_of_year", "is_weekend",
    ]
    target = "y_units_h7"

    tr = pd.read_parquet(train_frame.path)
    ho = pd.read_parquet(holdout_frame.path)

    reg = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=42,
    )
    reg.fit(tr[feat_cols], tr[target],
            eval_set=[(ho[feat_cols], ho[target])],
            verbose=False)

    reg.save_model(model.path + ".json")
    model.metadata["framework"] = "xgboost==1.5.2"
    model.metadata["params"] = json.dumps({
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "learning_rate": learning_rate,
    })
