output "runner_sa_email" {
  value       = google_service_account.kfp_runner.email
  description = "gsa used by the pipeline-runner ksa via workload identity"
}

output "artifact_bucket_uri" {
  value = "gs://${google_storage_bucket.kfp_artifacts.name}"
}
