"""forecast eval metrics.

wmape is the retail industry-standard (weighted mean absolute percent error).
bias is the signed error normalized by demand.
"""
from typing import Dict
import numpy as np


def mae(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    return float(np.mean(np.abs(y - yhat)))


def rmse(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def wmape(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    denom = np.sum(np.abs(y))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y - yhat)) / denom)


def bias(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    denom = np.sum(np.abs(y))
    if denom == 0:
        return float("nan")
    return float(np.sum(yhat - y) / denom)


def report(y, yhat) -> Dict[str, float]:
    return {
        "mae": mae(y, yhat),
        "rmse": rmse(y, yhat),
        "wmape": wmape(y, yhat),
        "bias": bias(y, yhat),
    }
