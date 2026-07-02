import pandas as pd

from main import prepare_series, detect_seasonality


def test_prepare_series_handles_missed_dates_and_zero_values():
    rows = [
        {"date": "1/1/2024", "value": 10},
        {"date": "1/3/2024", "value": 0},
        {"date": "1/4/2024", "value": 20},
        {"date": "1/6/2024", "value": 18},
    ]

    series = prepare_series(rows, "Day")

    assert len(series) >= 4
    assert series.isna().sum() == 0
    assert series.index.is_monotonic_increasing


def test_detect_seasonality_returns_none_for_short_series():
    series = pd.Series([4, 6, 8, 10, 12, 14], index=pd.date_range("2024-01-01", periods=6, freq="MS"))

    assert detect_seasonality(series, "Month") is None
