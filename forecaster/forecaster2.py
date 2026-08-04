from __future__ import annotations

from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
except ImportError:  # pragma: no cover - optional dependency for deployment
    ExponentialSmoothing = None

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover - optional dependency
    Prophet = None

st.set_page_config(page_title="NEX", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False)
def parse_monthly_data(raw_text: str) -> pd.DataFrame:
    rows: List[Tuple[pd.Timestamp, float]] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "," not in line:
            raise ValueError(f"Invalid line format: {raw_line}")

        date_text, value_text = (part.strip() for part in line.split(",", 1))
        try:
            parsed_date = pd.to_datetime(date_text, format="%Y-%m")
        except ValueError as exc:
            raise ValueError(f"Invalid date: {date_text}") from exc

        try:
            value = float(value_text)
        except ValueError as exc:
            raise ValueError(f"Invalid value: {value_text}") from exc

        rows.append((parsed_date, value))

    if len(rows) < 36:
        raise ValueError("Please enter at least 36 monthly data points.")

    df = pd.DataFrame(rows, columns=["date", "value"])
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def generate_forecast(df: pd.DataFrame) -> Dict[str, List[Tuple[str, float]]]:
    values = df["value"].astype(float).to_list()
    if len(values) < 3:
        raise ValueError("Please enter at least 3 data points.")

    predictions_by_method: Dict[str, List[Tuple[str, float]]] = {}

    recent_values = values[-3:]
    average_recent = sum(recent_values) / len(recent_values)
    current_method_predictions: List[Tuple[str, float]] = []
    for offset in range(1, 4):
        next_month = df["date"].iloc[-1] + pd.DateOffset(months=offset)
        current_method_predictions.append((next_month.strftime("%Y-%m"), round(average_recent, 2)))
    predictions_by_method["3-Month Avg"] = current_method_predictions

    if len(values) >= 36:
        monthly_index = pd.date_range(df["date"].min(), periods=len(values), freq="MS")
        monthly_series = pd.Series(values, index=monthly_index)

        if ExponentialSmoothing is not None:
            try:
                model = ExponentialSmoothing(
                    monthly_series,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=12,
                    initialization_method="estimated",
                )
                fitted_model = model.fit(optimized=True, use_brute=True)
                forecast_values = fitted_model.forecast(3)
                ets_predictions: List[Tuple[str, float]] = []
                for offset, value in enumerate(forecast_values.tolist(), start=1):
                    next_month = df["date"].iloc[-1] + pd.DateOffset(months=offset)
                    ets_predictions.append((next_month.strftime("%Y-%m"), round(float(value), 2)))
                predictions_by_method["Holt-Winters (ETS)"] = ets_predictions
            except Exception:
                predictions_by_method["Holt-Winters (ETS)"] = current_method_predictions
        else:
            predictions_by_method["Holt-Winters (ETS)"] = current_method_predictions

        if Prophet is not None:
            prophet_df = pd.DataFrame(
                {
                    "ds": pd.to_datetime(df["date"].dt.strftime("%Y-%m-%d")),
                    "y": df["value"].astype(float),
                }
            )
            prophet_model = Prophet(  # type: ignore[call-arg]
                yearly_seasonality="auto",
                weekly_seasonality=False,  # type: ignore[arg-type]
                daily_seasonality=False,  # type: ignore[arg-type]
            )
            prophet_model.fit(prophet_df)
            future = prophet_model.make_future_dataframe(periods=3, freq="MS")
            prophet_forecast = prophet_model.predict(future)
            prophet_predictions: List[Tuple[str, float]] = []
            for _, row in prophet_forecast.tail(3).iterrows():
                prophet_predictions.append((row["ds"].strftime("%Y-%m"), round(float(row["yhat"]), 2)))
            predictions_by_method["Prophet"] = prophet_predictions

    return predictions_by_method


def render_app() -> None:
    st.markdown(
        "<h1 style='color: #38bdf8; font-size: 3rem; font-weight: 700;'>NEX</h1>",
        unsafe_allow_html=True,
    )
    st.subheader("Forecast seasonal inventory, call volumes, service requests, and more with confidence.")

    input_text = st.text_area(
        label="",
        placeholder=(
            "Paste or type your monthly data here.\n"
            "Enter at least 36 monthly data points.\n"
            "Use one row per month in this format:\n"
            "YYYY-MM, value\n"
            "Example:\n"
            "2026-01, 1002\n"
            "2026-02, 2365\n"
            "2026-03, 3150"
        ),
        height=220,
    )

    if st.button("Submit and Generate Forecast", use_container_width=True):
        if not input_text.strip():
            st.warning("Please enter some monthly data first.")
            return

        try:
            df = parse_monthly_data(input_text)
            forecast_rows_by_method = generate_forecast(df)

            st.success("Forecast generated successfully")

            historical_df = pd.DataFrame(
                {
                    "Month": [item.strftime("%Y-%m") for item in df["date"]],
                    "Value": df["value"].astype(float),
                    "Series": "Observed",
                }
            )

            for method_name, forecast_rows in forecast_rows_by_method.items():
                st.subheader(method_name)
                method_df = pd.DataFrame(forecast_rows, columns=["Month", "Forecast"])
                st.dataframe(method_df, use_container_width=True)

            trend_frames = [historical_df]
            for method_name, forecast_rows in forecast_rows_by_method.items():
                forecast_df = pd.DataFrame(
                    {
                        "Month": [month for month, _ in forecast_rows],
                        "Value": [value for _, value in forecast_rows],
                    }
                )
                connected_forecast_df = pd.concat(
                    [historical_df.tail(1), forecast_df],
                    ignore_index=True,
                )
                connected_forecast_df["Series"] = method_name
                trend_frames.append(connected_forecast_df)

            trend_df = pd.concat(trend_frames, ignore_index=True)

            st.subheader("Data trend")
            chart = (
                alt.Chart(trend_df)
                .mark_line(strokeWidth=3)
                .encode(
                    x=alt.X("Month:N", title="Month"),
                    y=alt.Y("Value:Q", title="Value"),
                    color=alt.Color("Series:N", title="Method"),
                )
            )
            st.altair_chart(chart, use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    render_app()
