from __future__ import annotations

from typing import List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NEX", page_icon="📈", layout="wide")


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

    if len(rows) < 3:
        raise ValueError("Please enter at least 3 monthly data points.")

    df = pd.DataFrame(rows, columns=["date", "value"])
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


def generate_forecast(df: pd.DataFrame) -> List[Tuple[str, float]]:
    values = df["value"].astype(float).to_list()
    if len(values) < 3:
        raise ValueError("Please enter at least 3 data points.")

    recent_values = values[-3:]
    average_recent = sum(recent_values) / len(recent_values)

    predictions: List[Tuple[str, float]] = []
    for offset in range(1, 4):
        next_month = df["date"].iloc[-1] + pd.DateOffset(months=offset)
        predictions.append((next_month.strftime("%Y-%m"), round(average_recent, 2)))

    return predictions


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
            forecast_rows = generate_forecast(df)

            st.success("Forecast generated successfully")

            forecast_df = pd.DataFrame(forecast_rows, columns=["Month", "Forecast"])
            st.dataframe(forecast_df, use_container_width=True)

            historical_df = pd.DataFrame(
                {
                    "Month": [item.strftime("%Y-%m") for item in df["date"]],
                    "Value": df["value"].astype(float),
                    "Series": "Observed",
                }
            )
            forecast_df = pd.DataFrame(
                {
                    "Month": [month for month, _ in forecast_rows],
                    "Value": [value for _, value in forecast_rows],
                }
            )
            connected_forecast_df = pd.concat([historical_df.tail(1), forecast_df], ignore_index=True)

            st.subheader("Data trend")
            observed_chart = (
                alt.Chart(historical_df)
                .mark_line(color="#14b8a6", strokeWidth=3)
                .encode(
                    x=alt.X("Month:N", title="Month"),
                    y=alt.Y("Value:Q", title="Value"),
                )
            )
            forecast_chart = (
                alt.Chart(connected_forecast_df)
                .mark_line(color="#3b82f6", strokeWidth=3, strokeDash=[6, 4])
                .encode(
                    x=alt.X("Month:N", title="Month"),
                    y=alt.Y("Value:Q", title="Value"),
                )
            )
            st.altair_chart(observed_chart + forecast_chart, use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    render_app()
