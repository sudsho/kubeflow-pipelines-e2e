# service account used by the pipeline-runner pod. workload identity binds it to the ksa.

resource "google_service_account" "kfp_runner" {
  account_id   = "kfp-runner"
  display_name = "Kubeflow Pipelines Runner"
}

locals {
  runner_roles = [
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/aiplatform.user",
    "roles/artifactregistry.reader",
  ]
}

resource "google_project_iam_member" "kfp_runner_bindings" {
  for_each = toset(local.runner_roles)
  project  = var.project
  role     = each.value
  member   = "serviceAccount:${google_service_account.kfp_runner.email}"
}

# workload identity binding: ksa "kfp-runner" in namespace "kubeflow" acts as this GSA.
resource "google_service_account_iam_member" "kfp_runner_wi" {
  service_account_id = google_service_account.kfp_runner.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project}.svc.id.goog[kubeflow/kfp-runner]"
}
