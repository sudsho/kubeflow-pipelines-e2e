import pandas as pd
import pytest

from src.features.schema import FEATURE_COLS, TARGET, validate


def _mk_df(with_nulls=False):
    rows = 32
    df = pd.DataFrame({c: [float(i) for i in range(rows)] for c in FEATURE_COLS})
    df[TARGET] = [float(i) for i in range(rows)]
    if with_nulls:
        df.loc[3, TARGET] = None
    return df


def test_validate_ok():
    assert validate(_mk_df()) is True


def test_validate_missing_column():
    df = _mk_df()
    df = df.drop(columns=["dow"])
    with pytest.raises(ValueError):
        validate(df)


def test_validate_target_null():
    df = _mk_df(with_nulls=True)
    with pytest.raises(ValueError):
        validate(df)
