# GKE autopilot cluster for kubeflow pipelines.
# autopilot keeps node ops out of scope; we just need pods to schedule.

resource "google_container_cluster" "kfp" {
  name             = var.cluster_name
  location         = var.region
  enable_autopilot = true

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {}

  workload_identity_config {
    workload_pool = "${var.project}.svc.id.goog"
  }
}

output "gke_endpoint" {
  value = google_container_cluster.kfp.endpoint
}
