# kfp v1 notes

## update: ported to kfp 2.x

`kfp==1.8.13` does not install on modern Python (3.11+), so the pipeline was
ported to `kfp>=2.7`. The change was small because the code already targeted the
v2 SDK (`kfp.v2`): the imports moved from `kfp.v2.dsl` / `kfp.v2.compiler` to the
native `kfp.dsl` / `kfp.compiler` namespace (the `kfp.v2` shim in 2.x is
deprecated and slated for removal). The `dsl.Condition(step.outputs["passed"] ==
True, ...)` gate and typed `Input[...]` / `Output[...]` artifacts carry over
unchanged. `kfp.compiler.Compiler` emits an IR `PipelineSpec` (JSON) that
`dist/demand_forecast.json` holds after `make compile`.

The v1-era notes below are kept for historical context. The
`kfp.Client.run_pipeline` package-extension limitation is a v1 client concern and
does not apply to the 2.x path.

---

Notes accumulated while sketching this pipeline against `kfp==1.8.13`. Written
down so the next attempt does not repeat the same footguns.

## client / server pinning

We pin `kfp==1.8.13` on the client side and target a standalone install around
KFP `1.8.x`. Mixing client and server across minor versions can produce opaque
`unknown field` errors inside the compiled `PipelineSpec`.

## compilation and submission (open items)

`kfp.v2.compiler.Compiler` emits a JSON `PipelineSpec`. On `kfp==1.8.13`,
`kfp.Client.run_pipeline` only accepts package paths ending in `.tar.gz`,
`.tgz`, `.zip`, `.yaml`, or `.yml`, so the compiled `.json` cannot be handed
directly to `run_pipeline` on this client version. Running v2-style components
against a standalone v1 API server needs `create_run_from_pipeline_func` in a
v2-compatible mode, which this repo does not wire up. Treat the compile /
submit scripts here as scaffolding, not a working end-to-end path.

## component images

`base_image="python:3.9"` plus `packages_to_install=[...]` is convenient for
iteration but pip resolves packages every run. Once component contracts
stabilise, bake images into Artifact Registry and reference them with a pinned
digest.

## artifact IO patterns

Kubeflow v2 component functions get typed `Input[...]` and `Output[...]`
params. Do not write to `output.uri` directly; use `output.path` which the
runtime materialises to a mounted GCS-backed path.

## conditions

`with dsl.Condition(step.outputs["passed"] == True, name="..."):` is how the
"only register the model if the eval passed" gate is expressed. The `== True`
looks redundant but the KFP DSL requires the explicit comparison; a bare
truthy check silently no-ops.

## resource limits

Under Autopilot, request CPU / memory explicitly on any component you expect to
be heavy. The default 500m / 512Mi will not survive a large training step. Use
`.set_cpu_request`, `.set_memory_request`, and optionally
`.add_node_selector_constraint`. The pipeline in this repo does not set these
and would need them before it could scale.

## workload identity

Attach the ksa `kfp-runner` to the workflow's pods so BigQuery/GCS/Vertex calls
inherit the GSA identity. This avoids provisioning JSON key files.

## submitting from CI

`kfp.Client` reads `KFP_HOST` and the GCP-issued IAP token from ADC (application
default credentials). Store the OAuth client id as a repo secret; do not
hardcode.
