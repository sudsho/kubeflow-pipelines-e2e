"""compile the kfp pipeline into a package that can be submitted to kfp v1."""
import argparse
import pathlib

from kfp.v2 import compiler

from pipelines.demand_forecast import demand_forecast_pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/demand_forecast.json")
    args = ap.parse_args()
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    compiler.Compiler().compile(
        pipeline_func=demand_forecast_pipeline,
        package_path=args.out,
    )
    print(f"compiled to {args.out}")


if __name__ == "__main__":
    main()
