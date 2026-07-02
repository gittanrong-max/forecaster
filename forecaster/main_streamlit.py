from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
from statsmodels.tsa.holtwinters import ExponentialSmoothing


st.set_page_config(page_title="Forecaster", page_icon="📈", layout="wide")


def parse_date(value: str) -> pd.Timestamp:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return pd.Timestamp(datetime.strptime(value, fmt))
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def prepare_series(rows: list[dict[str, Any]], unit: str) -> pd.Series:
    if not rows:
        raise ValueError("At least one data point is required.")

    records: list[tuple[pd.Timestamp, float]] = []
    for row in rows:
        try:
            ts = parse_date(str(row["date"]))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        value = row.get("value")
        if value is None or value == "":
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric value: {value}") from exc

        if np.isnan(numeric_value):
            continue

        records.append((ts, numeric_value))

    if len(records) < 2:
        raise ValueError("At least two valid data points are required.")

    df = pd.DataFrame(records, columns=["date", "value"])
    df = df.sort_values("date")
    df = df.drop_duplicates(subset=["date"], keep="last")

    freq = infer_frequency(unit)
    full_index = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq=freq)
    series = df.set_index("date")["value"].reindex(full_index)

    series = series.replace(0, np.nan)
    series = series.ffill().bfill()

    if series.isna().all():
        raise ValueError("The series contains no usable numeric values after cleaning.")

    return series.astype(float)


def infer_frequency(unit: str) -> str:
    mapping = {
        "Year": "YS",
        "Quarter": "QS",
        "Month": "MS",
        "Day": "D",
    }
    return mapping.get(unit, "MS")


def detect_seasonality(series: pd.Series, unit: str) -> int | None:
    if len(series) < 12:
        return None

    candidate_periods = {
        "Year": [12],
        "Quarter": [4],
        "Month": [12, 6, 3],
        "Day": [7, 30],
    }
    periods = candidate_periods.get(unit, [12])

    for period in periods:
        if len(series) < period * 2:
            continue
        seasonal_values = series.dropna().tail(period * 2)
        if len(seasonal_values) < period * 2:
            continue

        if np.ptp(seasonal_values) == 0:
            continue

        return period

    return None


def build_forecast(series: pd.Series, forecast_periods: int, unit: str) -> tuple[list[dict[str, Any]], str, list[str]]:
    seasonal_period = detect_seasonality(series, unit)
    notes: list[str] = []

    if seasonal_period:
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_period,
            initialization_method="estimated",
        )
        fitted = model.fit(optimized=True)
        forecast_values = fitted.forecast(forecast_periods)
        model_used = f"Exponential Smoothing (seasonal, period={seasonal_period})"
        notes.append(f"Detected seasonality with period {seasonal_period}.")
    else:
        model = ExponentialSmoothing(series, trend="add", seasonal=None, initialization_method="estimated")
        fitted = model.fit(optimized=True)
        forecast_values = fitted.forecast(forecast_periods)
        model_used = "Exponential Smoothing (non-seasonal)"
        notes.append("No strong seasonality detected; used a non-seasonal model.")

    output = []
    for idx, value in enumerate(forecast_values.tolist()):
        forecast_date = (series.index[-1] + pd.tseries.frequencies.to_offset(infer_frequency(unit)) * (idx + 1)).strftime("%Y-%m-%d")
        output.append({"date": forecast_date, "value": round(float(value), 2)})

    if series.isna().sum() > 0:
        notes.append("Missing values were filled using forward/backward filling before modeling.")

    return output, model_used, notes


def main() -> None:
    st.title("📈 Forecasting App")
    st.caption("Edit the time series below, choose a forecast range, and generate predictions.")

    default_rows = [
        {"date": "2020-01-01", "value": 100},
        {"date": "2020-02-01", "value": 110},
        {"date": "2020-03-01", "value": 105},
        {"date": "2020-04-01", "value": 125},
        {"date": "2020-05-01", "value": 130},
        {"date": "2020-06-01", "value": 140},
        {"date": "2020-07-01", "value": 145},
        {"date": "2020-08-01", "value": 155},
        {"date": "2020-09-01", "value": 160},
        {"date": "2020-10-01", "value": 170},
        {"date": "2020-11-01", "value": 175},
        {"date": "2020-12-01", "value": 185},
    ]

    df = pd.DataFrame(default_rows)

    with st.sidebar:
        st.header("Configuration")
        unit = st.selectbox("Time unit", ["Month", "Quarter", "Year", "Day"], index=0)
        forecast_start = st.date_input("Forecast start", value=datetime(2021, 1, 1).date())
        forecast_end = st.date_input("Forecast end", value=datetime(2021, 3, 1).date())

    st.subheader("Historical data")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "date": st.column_config.TextColumn("Date", required=True),
            "value": st.column_config.NumberColumn("Value", required=True),
        },
    )

    if st.button("Generate forecast", use_container_width=True):
        try:
            rows = [
                {"date": str(row["date"]), "value": row["value"]}
                for row in edited_df.to_dict(orient="records")
                if row.get("date") not in (None, "") and row.get("value") not in (None, "")
            ]
            series = prepare_series(rows, unit)

            start_date = parse_date(forecast_start.strftime("%Y-%m-%d"))
            end_date = parse_date(forecast_end.strftime("%Y-%m-%d"))
            if start_date > end_date:
                raise ValueError("Forecast start date must be before or equal to the forecast end date.")

            freq = infer_frequency(unit)
            horizon = pd.date_range(start=start_date, end=end_date, freq=freq)
            steps = len(horizon)
            if steps <= 0:
                raise ValueError("Forecast range must contain at least one step.")

            forecast_points, model_used, notes = build_forecast(series, steps, unit)

            st.success(model_used)
            for note in notes:
                st.info(note)

            forecast_df = pd.DataFrame(forecast_points)
            if not forecast_df.empty:
                st.subheader("Forecast results")
                st.dataframe(forecast_df, use_container_width=True)

                history_df = pd.DataFrame({"date": series.index.strftime("%Y-%m-%d"), "value": series.values})
                history_df["source"] = "historical"
                forecast_df["source"] = "forecast"
                plot_df = pd.concat([history_df, forecast_df], ignore_index=True)
                plot_df["date"] = pd.to_datetime(plot_df["date"])
                plot_df = plot_df.sort_values("date")

                st.line_chart(plot_df.set_index("date")["value"])
        except ValueError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    main()
