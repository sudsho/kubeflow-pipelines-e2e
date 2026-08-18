"""kfp component: run features.sql in bigquery and emit a parquet dataset on gcs.

Set ``DEMAND_FORECAST_SYNTHETIC=1`` to skip BigQuery/GCS entirely and emit a
synthetic demand dataset instead, so this component runs offline on CPU with no
credentials. The live BigQuery path is the default and is selected whenever that
env var is unset.
"""
from kfp.dsl import component, Output, Dataset


@component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-bigquery==3.0.1",
        "google-cloud-storage==2.3.0",
        "pyarrow==7.0.0",
        "db-dtypes==1.0.0",
        "pandas==1.4.2",
    ],
)
def read_bq_features(
    project: str,
    sql_gcs_uri: str,
    dest_table: str,
    features: Output[Dataset],
):
    """execute the features query and export result to a parquet artifact.

    Args:
        project: gcp project id.
        sql_gcs_uri: gs:// path to features.sql.
        dest_table: fully qualified `proj.dataset.table` for the query result.
        features: output kfp dataset (parquet on the pipeline artifact store).
    """
    import os

    if os.environ.get("DEMAND_FORECAST_SYNTHETIC") == "1":
        # offline path: no BigQuery, no GCS, no credentials.
        from src.features.synthetic import generate_raw_features

        generate_raw_features().to_parquet(features.path, index=False)
        return

    from google.cloud import bigquery, storage  # noqa: WPS433

    def _read_sql(uri: str) -> str:
        assert uri.startswith("gs://"), uri
        _, rest = uri[5:].split("/", 1)
        bucket, blob = rest.split("/", 1) if "/" in rest else (rest, "")
        client = storage.Client(project=project)
        return client.bucket(bucket).blob(blob).download_as_text()

    sql = _read_sql(sql_gcs_uri).format(project=project)
    bq = bigquery.Client(project=project)
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            destination=dest_table,
            write_disposition="WRITE_TRUNCATE",
        ),
    )
    job.result()

    df = bq.query(f"SELECT * FROM `{dest_table}`").to_dataframe()
    df.to_parquet(features.path)
