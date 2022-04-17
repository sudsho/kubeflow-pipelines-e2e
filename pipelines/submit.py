"""submit a compiled pipeline package to a KFP endpoint."""
import argparse
import os

import kfp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("KFP_HOST"))
    ap.add_argument("--package", default="dist/demand_forecast.json")
    ap.add_argument("--experiment", default="demand-forecast")
    ap.add_argument("--project", required=True)
    ap.add_argument("--region", default="us-central1")
    args = ap.parse_args()

    client = kfp.Client(host=args.host)
    exp = client.create_experiment(name=args.experiment)
    run = client.run_pipeline(
        experiment_id=exp.id,
        job_name="demand-forecast-run",
        pipeline_package_path=args.package,
        params={"project": args.project, "region": args.region},
    )
    print(f"submitted run={run.id} url={args.host}/#/runs/details/{run.id}")


if __name__ == "__main__":
    main()
