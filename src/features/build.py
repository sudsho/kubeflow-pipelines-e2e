"""build feature table by running features.sql in bigquery and writing to gcs parquet.

reads sql/features.sql from disk, substitutes project name, runs the query as a
scheduled bigquery job, then exports the result to a gcs parquet path.
"""
import argparse
import logging
import pathlib

from google.cloud import bigquery

log = logging.getLogger(__name__)


def load_sql(path):
    text = pathlib.Path(path).read_text()
    return text


def run(project, sql_path, dest_table, dest_uri):
    client = bigquery.Client(project=project)
    sql = load_sql(sql_path).format(project=project)

    job_config = bigquery.QueryJobConfig(
        destination=dest_table,
        write_disposition="WRITE_TRUNCATE",
    )
    log.info("submitting features query to bigquery, dest=%s", dest_table)
    q = client.query(sql, job_config=job_config)
    q.result()

    log.info("exporting features to %s", dest_uri)
    extract = client.extract_table(
        dest_table,
        dest_uri,
        job_config=bigquery.ExtractJobConfig(destination_format="PARQUET"),
    )
    extract.result()
    log.info("features build done. rows=%s", q.total_rows)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--sql", default="sql/features.sql")
    p.add_argument("--dest-table", required=True)
    p.add_argument("--dest-uri", required=True, help="gs://bucket/path/features-*.parquet")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    a = parse_args()
    run(a.project, a.sql, a.dest_table, a.dest_uri)
