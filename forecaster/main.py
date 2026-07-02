from __future__ import annotations

from datetime import datetime
from typing import Any, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from statsmodels.tsa.holtwinters import ExponentialSmoothing

app = FastAPI(title="Forecaster API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ForecastRow(BaseModel):
    date: str
    value: float


class ForecastRequest(BaseModel):
    rows: List[ForecastRow]
    forecast_start: str
    forecast_end: str
    unit: str = "Month"


class ForecastResponse(BaseModel):
    forecast: List[dict[str, Any]]
    model_used: str
    notes: List[str]


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

    records = []
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
        output.append({"date": (series.index[-1] + pd.tseries.frequencies.to_offset(infer_frequency(unit)) * (idx + 1)).strftime("%Y-%m-%d"), "value": round(float(value), 2)})

    if series.isna().sum() > 0:
        notes.append("Missing values were filled using forward/backward filling before modeling.")

    return output, model_used, notes


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/forecast", response_model=ForecastResponse)
def forecast(payload: ForecastRequest) -> ForecastResponse:
    try:
        series = prepare_series([row.model_dump() for row in payload.rows], payload.unit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        start_date = parse_date(payload.forecast_start)
        end_date = parse_date(payload.forecast_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Forecast start date must be before or equal to the forecast end date.")

    freq = infer_frequency(payload.unit)
    horizon = pd.date_range(start=start_date, end=end_date, freq=freq)
    steps = len(horizon)
    if steps <= 0:
        raise HTTPException(status_code=400, detail="Forecast range must contain at least one step.")

    forecast_points, model_used, notes = build_forecast(series, steps, payload.unit)
    return ForecastResponse(forecast=forecast_points, model_used=model_used, notes=notes)
