import pandas as pd

from main import prepare_series, detect_seasonality
from main_streamlit import generate_forecasts, parse_series_input


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


def test_parse_series_input_returns_series_with_month_labels():
    text = "2026-01, 1008\n2026-02, 2054\n2026-03, 2611"

    series = parse_series_input(text)

    assert len(series) == 3
    assert series.index[0].strftime("%Y-%m") == "2026-01"
    assert series.iloc[0] == 1008


def test_generate_forecasts_returns_three_months_for_each_method():
    dates = pd.date_range("2024-01-01", periods=36, freq="MS")
    values = [100 + i * 5 + (i % 12) * 6 for i in range(36)]
    series = pd.Series(values, index=dates)

    forecasts = generate_forecasts(series, horizon=3)

    assert set(forecasts) == {"Holt-Winters (ETS)", "SARIMA", "Prophet"}
    for forecast in forecasts.values():
        assert len(forecast) == 3
