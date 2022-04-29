# GKE setup

## prerequisites

- gcloud >= 380
- kubectl >= 1.22
- terraform >= 1.1
- billing enabled on the project
- APIs enabled: `container.googleapis.com`, `storage.googleapis.com`,
  `bigquery.googleapis.com`, `aiplatform.googleapis.com`, `iam.googleapis.com`

## Terraform apply

```bash
cd terraform
terraform init
terraform apply \
  -var project=$GCP_PROJECT \
  -var region=$GCP_REGION \
  -var cluster_name=$GKE_CLUSTER \
  -var artifact_bucket=$GCS_BUCKET
```

The apply creates:

- a GKE Autopilot cluster (`kfp-cluster-1`)
- a versioned GCS bucket used as the KFP pipeline_root
- a `kfp-runner` GSA with BigQuery, Storage, and Vertex AI roles
- a workload-identity binding so the in-cluster `kfp-runner` KSA can act as the GSA

## kubectl

```bash
gcloud container clusters get-credentials $GKE_CLUSTER --region $GCP_REGION
kubectl get nodes -o wide
```

## KFP standalone install

Follow `k8s/README.md`. We pin to KFP 1.8.1 so the client (`kfp==1.8.13`) matches the
server-side APIs; mismatched client/server versions produce cryptic
`PipelineSpec` errors.

## verify

```bash
kubectl -n kubeflow get pods -w
# ml-pipeline, ml-pipeline-persistenceagent, ml-pipeline-scheduledworkflow,
# workflow-controller, minio, mysql should all be Running.

kubectl -n kubeflow port-forward svc/ml-pipeline-ui 8080:80
open http://localhost:8080
```

## teardown

```bash
cd terraform
terraform destroy -var project=$GCP_PROJECT -var artifact_bucket=$GCS_BUCKET
```
