"""smoke test: pipeline modules import cleanly."""
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
    importlib.import_module(mod)
