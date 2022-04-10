"""light wrapper around a saved xgb booster for online prediction."""
import logging
import pathlib
from typing import Dict, List

import numpy as np
import xgboost as xgb

from src.features.schema import FEATURE_COLS

log = logging.getLogger(__name__)


class Predictor:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None

    def load(self):
        if not pathlib.Path(self.model_path).exists():
            raise FileNotFoundError(self.model_path)
        m = xgb.XGBRegressor()
        m.load_model(self.model_path)
        self._model = m
        log.info("loaded booster from %s", self.model_path)

    def predict_one(self, features: Dict[str, float]) -> float:
        if self._model is None:
            self.load()
        row = np.array([[features.get(c, 0.0) for c in FEATURE_COLS]], dtype=np.float64)
        return float(self._model.predict(row)[0])

    def predict_batch(self, rows: List[Dict[str, float]]) -> List[float]:
        if self._model is None:
            self.load()
        mat = np.array(
            [[r.get(c, 0.0) for c in FEATURE_COLS] for r in rows],
            dtype=np.float64,
        )
        return [float(v) for v in self._model.predict(mat)]
