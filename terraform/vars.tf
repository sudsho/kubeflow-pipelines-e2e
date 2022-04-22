variable "project" {
  type        = string
  description = "gcp project id"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "cluster_name" {
  type    = string
  default = "kfp-cluster-1"
}

variable "artifact_bucket" {
  type        = string
  description = "gcs bucket for KFP pipeline_root and model staging"
}
