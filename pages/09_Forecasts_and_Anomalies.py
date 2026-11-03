import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pulseiq.app_common import department_picker, ensure_database, insight, money, query_df, require_user


st.title("AI signals, anomalies and forecasts")
st.caption("Model outputs are decision-support signals. They are not verified events or actual results.")

if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] == "MANAGER":
    st.info("Company anomaly and workforce forecast details are limited to HR, Admin and Executive personas.")
    st.stop()

department = department_picker(user)
freshness = query_df("SELECT * FROM metrics.dashboard_data_freshness")
if not freshness.empty:
    fresh = freshness.iloc[0]
    st.caption(
        f"Warehouse refreshed {pd.Timestamp(fresh.last_successful_refresh):%d %b %Y %H:%M UTC}; "
        f"observed data cut-off {pd.Timestamp(fresh.data_cutoff):%d %b %Y}."
    )

st.subheader("Anomalies by type and reported amount at risk")
anomalies = query_df(
    """SELECT source_dataset, reason_code AS anomaly_type,
              COUNT(*) FILTER (WHERE flagged='Y') AS flagged_rows,
              SUM(CASE WHEN flagged='Y' THEN COALESCE(money_at_risk,0) ELSE 0 END) AS money_at_risk
       FROM clean.fact_anomaly
       GROUP BY 1,2
       HAVING COUNT(*) FILTER (WHERE flagged='Y') > 0
       ORDER BY money_at_risk DESC, flagged_rows DESC, source_dataset, anomaly_type"""
)
st.warning("Anomaly flags are prompts for human review, not proof of fraud or error. Reported money at risk is a model amount, not a confirmed loss. Employee identifiers are not displayed.")
if not anomalies.empty:
    anomalies["type"] = anomalies.source_dataset.astype(str) + " · " + anomalies.anomaly_type.astype(str)
    total_flags = int(anomalies.flagged_rows.sum())
    total_risk = float(anomalies.money_at_risk.sum())
    c1, c2 = st.columns(2)
    c1.metric("Flagged records", f"{total_flags:,}")
    c2.metric("Reported money at risk", money(total_risk))

    st.caption("AI-generated, for human review. Types are ranked by reported money at risk; amounts are not confirmed losses.")
    anomaly_chart = px.bar(
        anomalies.sort_values("money_at_risk", ascending=True),
        x="money_at_risk",
        y="type",
        orientation="h",
        title="AI-generated, for human review · Anomalies ranked by money at risk",
        hover_data={"flagged_rows": True, "money_at_risk": ":,.0f", "source_dataset": True, "anomaly_type": True, "type": False},
        color_discrete_sequence=["#D17B0F"],
    )
    anomaly_chart.update_layout(template="plotly_white", xaxis_title="Reported risk amount (INR)", yaxis_title=None)
    st.plotly_chart(anomaly_chart, use_container_width=True)
    st.dataframe(
        anomalies[["source_dataset", "anomaly_type", "flagged_rows", "money_at_risk"]].style.format(
            {"flagged_rows": "{:,.0f}", "money_at_risk": "INR {:,.0f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    top = anomalies.iloc[0]
    insight(f"{top.anomaly_type} in {top.source_dataset} has the largest reported exposure at {money(top.money_at_risk)} across {top.flagged_rows:,.0f} flagged records.")
else:
    st.info("No flagged anomaly records are present in the supplied feed.")

st.subheader("Headcount forecast and observed actuals")
if department == "ALL":
    actuals = query_df("SELECT period, value AS actual FROM metrics.m01_headcount WHERE department_id='ALL' ORDER BY period")
    forecasts = query_df(
        """SELECT period, forecast_value, lower_80, upper_80, status
           FROM metrics.dashboard_forecast WHERE department_id='ALL' ORDER BY period"""
    )
else:
    actuals = query_df(
        "SELECT period, value AS actual FROM metrics.m01_headcount WHERE department_id=? ORDER BY period",
        [department],
    )
    forecasts = query_df(
        """SELECT period, forecast_value, lower_80, upper_80, status
           FROM metrics.dashboard_forecast WHERE department_id=? ORDER BY period""",
        [department],
    )

if not forecasts.empty:
    forecasts["period"] = pd.to_datetime(forecasts.period)
    actuals["period"] = pd.to_datetime(actuals.period)
    comparison = forecasts.merge(actuals, on="period", how="left")
    comparison["error"] = comparison.actual - comparison.forecast_value
    comparison["absolute_error"] = comparison.error.abs()
    comparison["absolute_percentage_error"] = comparison.absolute_error / comparison.actual.abs() * 100

    st.caption("AI-generated, for human review. The shaded 80% interval shows a range; the forecast line is not a promise.")
    forecast_chart = go.Figure()
    forecast_chart.add_trace(
        go.Scatter(
            x=forecasts.period,
            y=forecasts.upper_80,
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    forecast_chart.add_trace(
        go.Scatter(
            x=forecasts.period,
            y=forecasts.lower_80,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(17,124,120,.18)",
            name="80% forecast range",
        )
    )
    forecast_chart.add_trace(
        go.Scatter(
            x=actuals.period,
            y=actuals.actual,
            mode="lines+markers",
            name="Observed actual",
            line={"color": "#14213d", "width": 3},
        )
    )
    forecast_chart.add_trace(
        go.Scatter(
            x=forecasts.period,
            y=forecasts.forecast_value,
            mode="lines+markers",
            name="Forecast",
            line={"color": "#117C78", "width": 3, "dash": "dash"},
        )
    )
    forecast_chart.update_layout(
        template="plotly_white",
        title="AI-generated, for human review · Headcount forecast with 80% range",
        xaxis_title="Month",
        yaxis_title="Employees",
        legend_title=None,
    )
    st.plotly_chart(forecast_chart, use_container_width=True)

    known_errors = comparison.dropna(subset=["actual"]).copy()
    if known_errors.empty:
        st.info("Forecast error is not calculable yet: supplied actuals end in September 2026 and the forecast starts in October 2026, so there are no overlapping months.")
        error_table = pd.DataFrame(
            columns=["Month", "Actual", "Forecast", "Error (actual - forecast)", "Absolute error", "Absolute percentage error"]
        )
        st.dataframe(error_table, hide_index=True, use_container_width=True)
    else:
        known_errors["Month"] = known_errors.period.dt.strftime("%b %Y")
        known_errors = known_errors.rename(
            columns={
                "actual": "Actual",
                "forecast_value": "Forecast",
                "error": "Error (actual - forecast)",
                "absolute_error": "Absolute error",
                "absolute_percentage_error": "Absolute percentage error",
            }
        )
        error_cols = ["Month", "Actual", "Forecast", "Error (actual - forecast)", "Absolute error", "Absolute percentage error"]
        st.dataframe(known_errors[error_cols].style.format("{:.1f}"), hide_index=True, use_container_width=True)
        st.metric("Mean absolute error", f"{known_errors['Absolute error'].mean():,.1f} employees")
        mape_rows = known_errors.loc[known_errors["Actual"].ne(0), "Absolute percentage error"]
        st.metric("Mean absolute percentage error", f"{mape_rows.mean():.1f}%" if not mape_rows.empty else "Not defined")
        insight("The error table compares observed headcount with the forecast for matching months; inspect the horizon and baseline before judging whether the error is acceptable.")
else:
    st.info("No forecast records exist for this scope.")

st.caption("The supplied forecast feed uses a linear trend with half-strength seasonality and is trained through September 2026. New actual data is required before forecast error can be measured.")
