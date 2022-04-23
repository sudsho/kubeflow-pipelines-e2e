# k8s / kubeflow install notes

We run Kubeflow Pipelines standalone on GKE Autopilot (1.22.x). Steps below assume
`gcloud`, `kubectl` and Terraform are set up locally.

## 1. cluster + bucket + IAM

```bash
cd terraform
terraform init
terraform apply -var project=$GCP_PROJECT -var artifact_bucket=$GCS_BUCKET
```

## 2. connect kubectl

```bash
gcloud container clusters get-credentials $GKE_CLUSTER --region $GCP_REGION
```

## 3. install KFP standalone

Uses the manifests pinned to KFP `1.8.1` (matches `kfp==1.8.13` client).

```bash
export PIPELINE_VERSION=1.8.1
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=$PIPELINE_VERSION"
```

## 4. pipeline runner service account

```bash
sed "s/PROJECT_ID/$GCP_PROJECT/g" k8s/pipeline-runner-sa.yaml | kubectl apply -f -
kubectl apply -f k8s/rbac.yaml
```

## 5. UI access

```bash
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80
open http://localhost:8080
```

## troubleshooting

- workflow controller crashloop: check the `argo` deployment, kfp 1.8.1 ships an older argo
  than autopilot's default kubelet expects. Pin argo to `v3.2.11` if you see this.
- object-storage errors from the metadata writer: confirm the pipeline root bucket exists
  and the runner GSA has `roles/storage.objectAdmin` on it.
