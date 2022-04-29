# kfp v1 notes

Notes we accumulated getting a first pipeline into production. Written down so the next
project does not repeat the same footguns.

## client / server pinning

Use `kfp==1.8.13` on the client and pin the standalone install to KFP `1.8.1`. Any client
minor >= server minor breaks compilation with an opaque `unknown field` error inside the
`PipelineSpec` JSON.

## v1 vs v2-compiled-with-v1

The IR compiler `kfp.v2.compiler.Compiler` produces a JSON `PipelineSpec` that KFP
standalone can execute on the v1 API server. This is what we do here. We do **not** use
`kfp.compiler.Compiler` (which emits Argo YAML) because that path is deprecated for
non-trivial pipelines with `Output[Artifact]` types.

## component images

`base_image="python:3.9"` plus `packages_to_install=[...]` is convenient for iteration but
pip resolves packages every run. Once component contracts stabilise, bake images into
Artifact Registry and reference them with a pinned digest.

## artifact IO patterns

Kubeflow v2 component functions get typed `Input[...]` and `Output[...]` params. Do not
write to `output.uri` directly; use `output.path` which the runtime materialises to a
mounted GCS-backed path.

## conditions

`with dsl.Condition(step.outputs["passed"] == True, name="..."):` is how you express the
"only register the model if the eval passed" gate. The `== True` looks redundant but the
KFP DSL requires the explicit comparison; a bare truthy check silently no-ops.

## resource limits

Under Autopilot, request CPU / memory explicitly on any component you expect to be heavy.
The default 500m / 512Mi will crash the xgboost training step on anything but the smallest
grids. Set via `.add_node_selector_constraint`, `.set_cpu_request`, `.set_memory_request`.

## workload identity

Attach the ksa `kfp-runner` to the workflow's pods so BigQuery/GCS/Vertex calls inherit
the GSA identity. This avoids provisioning JSON key files (which have leaked in more than
one company we know).

## submitting from CI

`kfp.Client` reads `KFP_HOST` and the GCP-issued IAP token from ADC (application default
credentials). Store the OAuth client id as a repo secret; do not hardcode.
