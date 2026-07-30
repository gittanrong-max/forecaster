from __future__ import annotations

from typing import List, Tuple

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
    if len(values) < 2:
        raise ValueError("Please enter at least 2 data points.")

    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    average_change = sum(changes) / len(changes) if changes else 0.0

    predictions: List[Tuple[str, float]] = []
    last_value = values[-1]
    for offset in range(1, 4):
        next_value = last_value + (average_change * offset)
        next_month = df["date"].iloc[-1] + pd.DateOffset(months=offset)
        predictions.append((next_month.strftime("%Y-%m"), round(next_value, 2)))

    return predictions


def render_app() -> None:
    st.title("NEX")
    st.subheader("Forecast seasonal inventory, call volumes, service requests and more!")

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

            chart_df = pd.DataFrame(
                {
                    "Month": [item.strftime("%Y-%m") for item in df["date"]],
                    "Observed": df["value"].astype(float),
                }
            )
            st.line_chart(chart_df.set_index("Month"))
        except ValueError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    render_app()
