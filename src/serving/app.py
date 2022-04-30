"""fastapi serving app.

meant to run as a sidecar to a downloaded xgboost model (from vertex model registry
or gcs). health endpoint + single + batch prediction.
"""
import logging
import os
from typing import List

from fastapi import FastAPI, HTTPException

from src.serving.predictor import Predictor
from src.serving.schemas import PredictRequest, PredictResponse, BatchRequest, BatchResponse

log = logging.getLogger(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/xgb.json")

app = FastAPI(title="demand-forecast", version="0.3.0")
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


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(req: BatchRequest) -> BatchResponse:
    if len(req.rows) == 0:
        raise HTTPException(status_code=400, detail="empty batch")
    ys: List[float] = _predictor.predict_batch([r.features for r in req.rows])
    return BatchResponse(yhat=ys)
