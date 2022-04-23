#!/usr/bin/env bash
# install kubeflow pipelines standalone on the currently-selected GKE cluster.
# pin to a version whose server API matches our `kfp==1.8.13` client.
set -euo pipefail

export PIPELINE_VERSION=1.8.1

kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=$PIPELINE_VERSION"

echo "waiting for kubeflow namespace to be ready..."
kubectl -n kubeflow rollout status deploy/ml-pipeline --timeout=180s
kubectl -n kubeflow rollout status deploy/ml-pipeline-ui --timeout=180s

echo "ok. run 'kubectl -n kubeflow port-forward svc/ml-pipeline-ui 8080:80'"
