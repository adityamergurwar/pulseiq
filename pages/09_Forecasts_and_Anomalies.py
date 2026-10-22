import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, money, query_df, require_user

st.title("AI signals, anomalies and forecasts")
st.caption("Model outputs are decision-support signals. Forecasts are shown with their 80% range and are not actual results.")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user=require_user()
if user["role"]=="MANAGER":
    st.info("Company anomaly and workforce forecast details are limited to HR, Admin and executive personas.")
    st.stop()
dept=department_picker(user)

fresh=query_df("SELECT * FROM metrics.dashboard_data_freshness")
if not fresh.empty:
    st.caption(f"Warehouse refreshed {pd.Timestamp(fresh.iloc[0].last_successful_refresh):%d %b %Y %H:%M UTC}; observed data cut-off {pd.Timestamp(fresh.iloc[0].data_cutoff):%d %b %Y}.")

anom=query_df("""SELECT CAST(date_trunc('month',period) AS DATE) AS period,source_dataset,reason_code,
                     COUNT(*) AS records,COUNT(*) FILTER(WHERE flagged='Y') AS flagged_records,
                     SUM(COALESCE(money_at_risk,0)) AS money_at_risk
              FROM clean.fact_anomaly GROUP BY 1,2,3 ORDER BY period,source_dataset,reason_code""")
st.subheader("Anomaly service output")
st.warning("Anomaly flags identify records for review; they are not proof of fraud or error. Employee identifiers are not shown.")
if not anom.empty:
    flagged=anom.groupby("source_dataset",as_index=False).agg(flagged_records=("flagged_records","sum"),money_at_risk=("money_at_risk","sum"))
    total_risk=float(flagged.money_at_risk.sum())
    k1,k2=st.columns(2)
    k1.metric("Flagged records",f"{int(flagged.flagged_records.sum()):,}")
    k2.metric("Reported money at risk",money(total_risk))
    fig=px.bar(flagged.sort_values("flagged_records"),x="flagged_records",y="source_dataset",orientation="h",title="Attendance features contain the most model flags" if flagged.flagged_records.nunique()>1 else "Flagged records by source",color_discrete_sequence=["#D17B0F"])
    fig.update_layout(template="plotly_white",xaxis_title="Flagged scored rows",yaxis_title=None)
    st.plotly_chart(fig,use_container_width=True)
    insight(f"The feed contains {int(flagged.flagged_records.sum()):,} flagged rows; reported money at risk is {money(total_risk)} where the source supplies an amount.")
    by_reason=anom.groupby(["source_dataset","reason_code"],as_index=False).agg(flagged_records=("flagged_records","sum"),money_at_risk=("money_at_risk","sum")).sort_values("flagged_records",ascending=False)
    st.dataframe(by_reason,use_container_width=True,hide_index=True)

st.subheader("Headcount forecast")
st.info("The supplied forecast begins in October 2026 and actual headcount ends in September 2026. No forecast month overlaps observed actuals, so M28 forecast error is unavailable; the dashboard does not invent an accuracy score.")
if dept=="ALL":
    actual=query_df("SELECT period,value AS actual FROM metrics.m01_headcount WHERE department_id='ALL' ORDER BY 1")
    forecast=query_df("SELECT period,forecast_value,lower_80,upper_80,status FROM metrics.dashboard_forecast WHERE department_id='ALL' ORDER BY 1")
else:
    actual=query_df("SELECT period,value AS actual FROM metrics.m01_headcount WHERE department_id=? ORDER BY 1",[dept])
    forecast=query_df("SELECT period,forecast_value,lower_80,upper_80,status FROM metrics.dashboard_forecast WHERE department_id=? ORDER BY 1",[dept])
if not forecast.empty:
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=forecast.period,y=forecast.upper_80,mode="lines",line=dict(width=0),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=forecast.period,y=forecast.lower_80,mode="lines",line=dict(width=0),fill="tonexty",fillcolor="rgba(17,124,120,.18)",name="80% forecast range"))
    fig.add_trace(go.Scatter(x=actual.period,y=actual.actual,mode="lines+markers",name="Observed headcount",line=dict(color="#14213d",width=3)))
    fig.add_trace(go.Scatter(x=forecast.period,y=forecast.forecast_value,mode="lines+markers",name="Forecast",line=dict(color="#117C78",width=3,dash="dash")))
    fig.update_layout(template="plotly_white",title="Observed headcount ends before the forecast range begins",xaxis_title=None,yaxis_title="Employees",legend_title=None)
    st.plotly_chart(fig,use_container_width=True)
    last=forecast.iloc[-1]
    insight(f"The final supplied projection is {last.forecast_value:,.0f} for {pd.Timestamp(last.period):%b %Y}, with an 80% range of {last.lower_80:,.0f}–{last.upper_80:,.0f}.")
    st.dataframe(forecast,use_container_width=True,hide_index=True)
else:
    st.info("No forecast records exist for this scope.")

st.caption("Forecast values use the source baseline model: linear trend over 36 months with half-strength seasonality. The feed was trained through 2026-09.")
