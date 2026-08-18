"""offline smoke: compile the pipeline, then run the components on CPU.

Runs with NO cloud credentials, NO API keys, and NO large downloads. It:

1. compiles the KFP pipeline to a package and validates the emitted spec.
2. generates a synthetic demand dataset (seasonal + trend + noise).
3. runs the read / feature / train (xgboost) / evaluate components locally by
   invoking each component's underlying python function against tempfile-backed
   artifact stand-ins, exactly as the component body would run in a container.
4. prints real MAE / MAPE / WMAPE from the trained model on the holdout.

Exits 0 on success. This is the clone-and-run path; the GKE / BigQuery / Vertex
path needs cloud setup and is not exercised here.
"""
import argparse
import json
import os
import pathlib
import sys
import tempfile

# make `pipelines` and `src` importable when run as a script.
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEMAND_FORECAST_SYNTHETIC", "1")


class _Artifact:
    """minimal stand-in for a KFP artifact: exposes .path and .metadata."""

    def __init__(self, path):
        self.path = str(path)
        self.metadata = {}


class _Metrics(_Artifact):
    def __init__(self, path):
        super().__init__(path)
        self.values = {}

    def log_metric(self, key, value):
        self.values[key] = value


def _rule(title):
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def compile_pipeline(out_path):
    from kfp import compiler
    from pipelines.demand_forecast import demand_forecast_pipeline

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    compiler.Compiler().compile(
        pipeline_func=demand_forecast_pipeline,
        package_path=out_path,
    )
    spec = json.loads(pathlib.Path(out_path).read_text())
    comps = sorted(spec.get("components", {}).keys())
    root_dag = spec["root"]["dag"]["tasks"]
    print(f"compiled package : {out_path} ({pathlib.Path(out_path).stat().st_size} bytes)")
    print(f"pipeline name    : {spec['pipelineInfo']['name']}")
    print(f"components ({len(comps)})   : {', '.join(c.replace('comp-', '') for c in comps)}")
    print(f"root dag tasks   : {', '.join(sorted(root_dag.keys()))}")
    assert len(comps) >= 5, "expected at least 5 components in the compiled spec"
    print("validation       : OK (spec parsed, components present)")


def run_components(workdir):
    from pipelines.components.read_bq import read_bq_features
    from pipelines.components.features_op import build_training_frame
    from pipelines.components.train_xgb_op import train_xgb
    from pipelines.components.evaluate_op import evaluate
    from src.features.schema import FEATURE_COLS, TARGET
    from src.eval.metrics import report

    import pandas as pd

    w = pathlib.Path(workdir)
    raw = _Artifact(w / "raw_features.parquet")
    train_frame = _Artifact(w / "train.parquet")
    holdout_frame = _Artifact(w / "holdout.parquet")
    model = _Artifact(w / "model")
    prophet_forecast = _Artifact(w / "prophet.parquet")
    metrics = _Metrics(w / "metrics.json")

    # 1. read (offline synthetic path)
    read_bq_features.python_func(
        project="offline",
        sql_gcs_uri="gs://offline/sql/features.sql",
        dest_table="offline.retail_features.features_daily",
        features=raw,
    )
    raw_df = pd.read_parquet(raw.path)
    print(f"synthetic raw    : {raw_df.shape[0]} rows, "
          f"{raw_df.groupby(['store_id', 'sku_id']).ngroups} store-sku series")

    # 2. features -> train / holdout split
    build_training_frame.python_func(
        raw_features=raw,
        horizon_days=7,
        holdout_days=28,
        train_frame=train_frame,
        holdout_frame=holdout_frame,
    )
    tr_df = pd.read_parquet(train_frame.path)
    ho_df = pd.read_parquet(holdout_frame.path)
    print(f"train / holdout  : {tr_df.shape[0]} / {ho_df.shape[0]} rows")

    # 3. train xgboost
    train_xgb.python_func(
        train_frame=train_frame,
        holdout_frame=holdout_frame,
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        model=model,
    )
    booster_path = model.path + ".json"
    print(f"trained model    : {booster_path} "
          f"({pathlib.Path(booster_path).stat().st_size} bytes)")

    # empty (schema-correct) prophet forecast; the prophet baseline is optional
    # offline and left empty so evaluate exercises its merge/NaN handling.
    pd.DataFrame(columns=["store_id", "sku_id", "ds", "yhat"]).to_parquet(
        prophet_forecast.path, index=False)

    # 4. evaluate (gating component)
    out = evaluate.python_func(
        holdout_frame=holdout_frame,
        xgb_model=model,
        prophet_forecast=prophet_forecast,
        metrics=metrics,
        wmape_threshold=0.35,
    )

    # headline MAE / MAPE / WMAPE from the trained model on the holdout.
    import xgboost as xgb

    m = xgb.XGBRegressor()
    m.load_model(booster_path)
    yhat = m.predict(ho_df[FEATURE_COLS])
    rep = report(ho_df[TARGET].to_numpy(), yhat)

    _rule("HOLDOUT METRICS (xgboost, synthetic demand)")
    print(f"  MAE   : {rep['mae']:.3f} units")
    print(f"  MAPE  : {rep['mape'] * 100:.2f} %")
    print(f"  WMAPE : {rep['wmape'] * 100:.2f} %")
    print(f"  RMSE  : {rep['rmse']:.3f} units")
    print(f"  bias  : {rep['bias'] * 100:+.2f} %")
    print(f"  gate  : passed={out.passed} (wmape={out.wmape:.4f} <= 0.35)")
    return rep, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/demand_forecast.json")
    ap.add_argument("--keep", action="store_true", help="keep the temp workdir")
    args = ap.parse_args()

    _rule("STEP 1  compile pipeline")
    compile_pipeline(args.out)

    _rule("STEP 2  run components locally on synthetic demand data")
    workdir = tempfile.mkdtemp(prefix="demand_forecast_smoke_")
    try:
        rep, out = run_components(workdir)
    finally:
        if not args.keep:
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)

    _rule("SMOKE OK")
    print("pipeline compiled and components ran offline on CPU. exit 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
