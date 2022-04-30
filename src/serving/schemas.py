"""pydantic request / response schemas for the serving app."""
from typing import Dict, List

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    store_id: str
    sku_id: str
    features: Dict[str, float] = Field(..., description="feature name -> value")


class PredictResponse(BaseModel):
    store_id: str
    sku_id: str
    yhat: float


class BatchRow(BaseModel):
    features: Dict[str, float]


class BatchRequest(BaseModel):
    rows: List[BatchRow]


class BatchResponse(BaseModel):
    yhat: List[float]
