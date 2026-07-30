from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover - optional dependency
    Prophet = None

st.set_page_config(page_title="Nex", page_icon="📈", layout="wide")


def parse_date(value: str) -> pd.Timestamp:
    for fmt in ("%Y-%m", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return pd.Timestamp(datetime.strptime(value, fmt))
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def parse_series_input(text: str) -> pd.Series:
    rows: list[tuple[pd.Timestamp, float]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "," not in line:
            raise ValueError(f"Invalid line format: {raw_line}")

        date_text, value_text = (part.strip() for part in line.split(",", 1))
        try:
            parsed_date = parse_date(date_text)
        except ValueError as exc:
            raise ValueError(f"Invalid date {date_text}") from exc

        try:
            value = float(value_text)
        except ValueError as exc:
            raise ValueError(f"Invalid value {value_text}") from exc

        rows.append((parsed_date, value))

    if len(rows) < 24:
        raise ValueError("Please enter at least 24 months of data.")

    df = pd.DataFrame(rows, columns=["date", "value"])
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    index = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    series = df.set_index("date")["value"].reindex(index)
    return series.ffill().bfill().astype(float)


def generate_forecasts(series: pd.Series, horizon: int = 3) -> dict[str, list[dict[str, Any]]]:
    if len(series) < 24:
        raise ValueError("Please enter at least 24 months of data.")

    result: dict[str, list[dict[str, Any]]] = {}

    ets_model = ExponentialSmoothing(series, trend="add", seasonal="add", seasonal_periods=12, initialization_method="estimated")
    ets_fit = ets_model.fit(optimized=True)
    ets_forecast = ets_fit.forecast(horizon)
    result["Holt-Winters (ETS)"] = [
        {"date": (series.index[-1] + pd.offsets.MonthBegin(1) * (idx + 1)).strftime("%Y-%m"), "value": round(float(value), 2)}
        for idx, value in enumerate(ets_forecast.tolist())
    ]

    sarima_model = SARIMAX(series, order=(1, 0, 1), seasonal_order=(1, 0, 1, 12), trend="c")
    sarima_fit = sarima_model.fit(disp=False)
    sarima_forecast = sarima_fit.forecast(horizon)
    result["SARIMA"] = [
        {"date": (series.index[-1] + pd.offsets.MonthBegin(1) * (idx + 1)).strftime("%Y-%m"), "value": round(float(value), 2)}
        for idx, value in enumerate(sarima_forecast.tolist())
    ]

    if Prophet is None:
        result["Prophet"] = [
            {"date": (series.index[-1] + pd.offsets.MonthBegin(1) * (idx + 1)).strftime("%Y-%m"), "value": None}
            for idx in range(horizon)
        ]
    else:
        prophet_df = pd.DataFrame({"ds": pd.to_datetime(series.index.strftime("%Y-%m-%d")), "y": series.values})
        prophet_model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        prophet_model.fit(prophet_df)
        future = prophet_model.make_future_dataframe(periods=horizon, freq="MS")
        prophet_forecast = prophet_model.predict(future)
        result["Prophet"] = [
            {"date": row["ds"].strftime("%Y-%m"), "value": round(float(row["yhat"]), 2)}
            for _, row in prophet_forecast.tail(horizon).iterrows()
        ]

    return result


def render_app() -> None:
    st.title("Nex")
    st.subheader("Forecast seasonal inventory, call volumes, service requests and more!")

    st.text_area(
        "Instruction",
        value=(
            "Enter 24+ months of data in the format below, and we'll forecast the next 3 months for you!\n"
            "2026-01, 1008\n"
            "2026-02, 2054\n"
            "2026-03, 2611\n"
            "..."
        ),
        height=190,
        disabled=True,
    )

    input_text = st.text_area(
        label="",
        placeholder="2026-01, 1008\n2026-02, 2054\n2026-03, 2611",
        height=220,
    )

    if st.button("Submit and Get My Forecast", use_container_width=True):
        try:
            series = parse_series_input(input_text)
            forecasts = generate_forecasts(series, horizon=3)

            st.success("Forecast generated successfully")
            for name, rows in forecasts.items():
                st.subheader(name)
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

            st.subheader("Trend view")
            plot_frame = pd.DataFrame({"date": series.index.strftime("%Y-%m"), "value": series.values})
            st.line_chart(plot_frame.set_index("date"))
        except ValueError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    render_app()
