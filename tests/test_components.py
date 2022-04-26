"""smoke tests: pipeline compiles and components import."""
import importlib

import pytest


COMPONENT_MODS = [
    "pipelines.components.read_bq",
    "pipelines.components.features_op",
    "pipelines.components.train_xgb_op",
    "pipelines.components.prophet_op",
    "pipelines.components.evaluate_op",
    "pipelines.components.register_vertex_op",
]


@pytest.mark.parametrize("mod", COMPONENT_MODS)
def test_component_module_imports(mod):
    m = importlib.import_module(mod)
    # each module must export exactly one top-level component function
    from kfp.components import BaseComponent  # noqa: WPS433
    exported = [
        v for k, v in vars(m).items()
        if not k.startswith("_") and isinstance(v, BaseComponent)
    ]
    assert len(exported) == 1, mod


def test_pipeline_compiles(tmp_path):
    from kfp.v2 import compiler
    from pipelines.demand_forecast import demand_forecast_pipeline
    out = tmp_path / "spec.json"
    compiler.Compiler().compile(demand_forecast_pipeline, str(out))
    assert out.exists() and out.stat().st_size > 100
