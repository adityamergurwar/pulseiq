import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, pct, query_df, require_user

st.title("Attrition and predicted risk")
st.caption("Actual exits and model predictions are separated. Risk is displayed only in groups; this page never displays names.")
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role']=='MANAGER': st.info("Attrition detail is limited to HR and executive roles in this demo."); st.stop()
dept=department_picker(user)
if dept=='ALL':
    exits=query_df("SELECT period,value AS exits FROM metrics.m03_exits WHERE department_id='ALL' ORDER BY 1")
    rates=query_df("SELECT period,value AS rate FROM metrics.m04_attrition_monthly WHERE department_id='ALL' ORDER BY 1")
else:
    exits=query_df("SELECT period,exits FROM metrics.dashboard_attrition WHERE department_id=? ORDER BY 1",[dept])
    rates=query_df("SELECT period,attrition_pct AS rate FROM metrics.dashboard_attrition WHERE department_id=? ORDER BY 1",[dept])
if exits.empty: st.info("No sufficiently large group is available for this scope."); st.stop()
periods=pd.to_datetime(exits.period).dt.date.tolist()
start=st.sidebar.selectbox("Start month",periods,max(0,len(periods)-12),key="attrition_start")
exits=exits[pd.to_datetime(exits.period).dt.date>=start]
rates=rates[pd.to_datetime(rates.period).dt.date>=start]
if not exits.empty:
    fig=px.bar(exits,x="period",y="exits",title=f"Exits peaked at {exits.exits.max():,.0f} in {exits.loc[exits.exits.idxmax(),'period']:%b %Y}",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Exits")
    st.plotly_chart(fig,use_container_width=True)
    peak=exits.loc[exits.exits.idxmax()]
    insight(f"The selected group recorded {peak.exits:,.0f} exits in {peak.period:%b %Y}.")
if not rates.empty:
    fig=px.line(rates,x="period",y="rate",markers=True,title=f"Monthly attrition was {rates.rate.iloc[-1]:.1f}% in {rates.period.iloc[-1]:%b %Y}",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Attrition (%)")
    st.plotly_chart(fig,use_container_width=True)
    peak=rates.loc[rates.rate.idxmax()]
    insight(f"Monthly attrition peaked at {peak.rate:.1f}% in {peak.period:%b %Y}; the metric uses exits divided by starting headcount.")

if dept!='ALL':
    tenure=query_df("SELECT tenure_band,exits FROM metrics.dashboard_exit_tenure WHERE department_id=? ORDER BY exits DESC",[dept])
    reasons=query_df("SELECT reason,exits FROM metrics.dashboard_exit_reasons WHERE department_id=? ORDER BY exits DESC",[dept])
    c1,c2=st.columns(2)
    if not tenure.empty:
        fig=px.bar(tenure,x="tenure_band",y="exits",title=f"{tenure.iloc[0].tenure_band} is the largest tenure group among exits",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Tenure at exit",yaxis_title="Exits")
        c1.plotly_chart(fig,use_container_width=True)
        insight(f"{tenure.iloc[0].tenure_band} accounts for {tenure.iloc[0].exits:,.0f} exits in groups of five or more.")
    if not reasons.empty:
        fig=px.bar(reasons,x="reason",y="exits",title=f"{reasons.iloc[0].reason} is the largest recorded exit category",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Exits")
        c2.plotly_chart(fig,use_container_width=True)
        insight(f"The largest recorded category has {reasons.iloc[0].exits:,.0f} exits; source reason labels are not independently verified.")

st.subheader("Predicted attrition risk")
st.warning("Prediction, not fact or a decision signal. The supplied model note describes this as a baseline support signal for HR.")
if dept=='ALL':
    risk=query_df("SELECT risk_band,people,average_risk_score FROM metrics.dashboard_predicted_risk_company ORDER BY risk_band")
else:
    risk=query_df("SELECT risk_band,people,average_risk_score FROM metrics.dashboard_predicted_risk WHERE department_id=? ORDER BY risk_band",[dept])
if not risk.empty:
    fig=px.bar(risk,x="risk_band",y="people",title=f"{int(risk.people.sum()):,} people are in the latest grouped prediction snapshot",color_discrete_sequence=["#D17B0F"])
    fig.update_layout(template="plotly_white",xaxis_title="Predicted band",yaxis_title="Employees")
    st.plotly_chart(fig,use_container_width=True)
    high=risk[risk.risk_band=='High']
    high_count=int(high.people.sum()) if not high.empty else 0
    insight(f"The grouped model snapshot places {high_count:,} employees in the High band; no individual ranking is available.")
else:
    st.info("No risk group meets the minimum display size.")
