"""fastapi serving app.

meant to run as a sidecar to a downloaded xgboost model.
inline pydantic models for now, split into schemas.py once the surface grows.
"""
import logging
import os
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.serving.predictor import Predictor

log = logging.getLogger(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/xgb.json")


class PredictRequest(BaseModel):
    store_id: str
    sku_id: str
    features: Dict[str, float] = Field(..., description="feature name -> value")


class PredictResponse(BaseModel):
    store_id: str
    sku_id: str
    yhat: float


app = FastAPI(title="demand-forecast", version="0.1.0")
_predictor = Predictor(MODEL_PATH)


@app.on_event("startup")
def _startup():
    logging.basicConfig(level=logging.INFO)
    try:
        _predictor.load()
    except FileNotFoundError as e:
        log.warning("model not present at startup: %s", e)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_loaded": _predictor._model is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        y = _predictor.predict_one(req.features)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="model not loaded")
    return PredictResponse(store_id=req.store_id, sku_id=req.sku_id, yhat=y)
