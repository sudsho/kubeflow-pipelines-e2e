import numpy as np

from src.eval.metrics import mae, rmse, wmape, bias, report


def test_perfect_prediction():
    y = np.array([10.0, 20.0, 30.0])
    r = report(y, y)
    assert r["mae"] == 0.0
    assert r["rmse"] == 0.0
    assert r["wmape"] == 0.0
    assert r["bias"] == 0.0


def test_wmape_shape():
    y = np.array([10.0, 20.0])
    yhat = np.array([12.0, 18.0])
    assert abs(wmape(y, yhat) - (4.0 / 30.0)) < 1e-9


def test_bias_sign():
    y = np.array([10.0, 20.0])
    yhat = np.array([12.0, 22.0])
    assert bias(y, yhat) > 0

    yhat2 = np.array([8.0, 18.0])
    assert bias(y, yhat2) < 0


def test_mae_rmse():
    y = np.array([0.0, 0.0])
    yhat = np.array([3.0, 4.0])
    assert mae(y, yhat) == 3.5
    assert abs(rmse(y, yhat) - (25.0 / 2) ** 0.5) < 1e-9
