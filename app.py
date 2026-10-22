"""PulseIQ workforce overview. All measures come from governed metric views."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, money, pct, prior_month_headcount, query_df, require_user

st.set_page_config(page_title="PulseIQ | Workforce", page_icon="◉", layout="wide")
st.markdown("<style>.block-container{padding-top:1.8rem;max-width:1440px} h1{letter-spacing:-.035em}</style>", unsafe_allow_html=True)
st.title("PulseIQ | Workforce and headcount")
st.caption("Zenith Nova Technologies · fictional workforce data · governed metrics")
if not ensure_database():
    st.warning("Build the warehouse first by running `python etl.py` from the project root and check the refresh logs.")
    st.stop()
user=require_user()
if user["role"]=="MANAGER":
    st.info("The manager persona is limited to its own team. Open Team productivity for your scoped sprint view.")
    st.stop()
dept=department_picker(user)
dates=query_df("SELECT DISTINCT period FROM metrics.m01_headcount ORDER BY 1")
if dates.empty:
    st.info("No workforce metric rows are available.")
    st.stop()
date_values=pd.to_datetime(dates.period).dt.date.tolist()
selected=st.sidebar.selectbox("Month end",date_values,index=len(date_values)-1)
period=pd.Timestamp(selected).replace(day=1).date()
dept_sql="department_id=?"
trend=query_df(f"SELECT period,value AS headcount FROM metrics.m01_headcount WHERE {dept_sql} AND period<=? ORDER BY 1",[dept,selected])
current=query_df(f"SELECT SUM(value) AS value FROM metrics.m01_headcount WHERE {dept_sql} AND period=?",[dept,selected])
prior=prior_month_headcount(dept,selected)
hires=query_df(f"SELECT SUM(value) AS value FROM metrics.m02_hires WHERE {dept_sql} AND period=?",[dept,selected])
exits=query_df(f"SELECT SUM(value) AS value FROM metrics.m03_exits WHERE {dept_sql} AND period=?",[dept,selected])
cur=float(current.iloc[0,0] or 0) if not current.empty else 0
prev=float(prior.iloc[0,0] or 0) if not prior.empty else 0
hire_count=int(hires.iloc[0,0] or 0) if not hires.empty else 0
exit_count=int(exits.iloc[0,0] or 0) if not exits.empty else 0
delta=(cur-prev)/prev*100 if prev else 0
k1,k2,k3,k4=st.columns(4)
k1.metric("Month end headcount",f"{cur:,.0f}",f"{delta:+.1f}% vs prior month")
k2.metric("Hires",f"{hire_count:,}","selected month")
k3.metric("Exits",f"{exit_count:,}","selected month")
k4.metric("Net change",f"{hire_count-exit_count:+,}","hires less exits")

if not trend.empty:
    first=float(trend.head(1).headcount.iloc[0])
    total_change=(cur-first)/first*100 if first else 0
    direction="grew" if total_change>=0 else "fell"
    fig=px.line(trend,x="period",y="headcount",markers=True,
        title=f"Headcount {direction} {abs(total_change):.1f}% to {cur:,.0f}",
        color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Employees",showlegend=False,margin=dict(l=10,r=10,t=55,b=5))
    st.plotly_chart(fig,use_container_width=True)
    insight(f"The selected group has {cur:,.0f} employees at month end, {delta:+.1f}% from the prior month.")

if user["role"] == "ADMIN":
    mix=query_df("SELECT label,value FROM metrics.dashboard_department_mix WHERE period=? AND department_id<>'ALL' ORDER BY value DESC",[period])
    if not mix.empty:
        top=mix.iloc[0]
        fig=px.bar(mix.sort_values("value"),x="value",y="label",orientation="h",
          title=f"{top.label} is the largest department ({top.value:,.0f})",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Employees",yaxis_title=None,showlegend=False,margin=dict(l=10,r=10,t=55,b=5))
        st.plotly_chart(fig,use_container_width=True)
        insight(f"{top.label} has {top.value:,.0f} people, the largest department in {selected:%b %Y}.")
elif user["role"] in {"HR","MANAGER"}:
    st.info("Department mix is limited by the selected role. Manager personas see their team scope.")

if user["role"] in {"ADMIN","HR"}:
    group_id="ALL" if dept=="ALL" else dept
    params=[period,group_id]
    location=query_df("SELECT label,value FROM metrics.dashboard_location_tier WHERE period=? AND department_id=? ORDER BY value DESC",params)
    level=query_df("SELECT label,value FROM metrics.dashboard_level_mix WHERE period=? AND department_id=? ORDER BY value DESC",params)
    mode=query_df("SELECT label,value FROM metrics.dashboard_work_mode WHERE period=? AND department_id=? ORDER BY value DESC",params)
    c1,c2=st.columns(2)
    if not location.empty:
        top=location.iloc[0]
        fig=px.bar(location,x="label",y="value",title=f"Tier {top.label} has the largest workforce ({top.value:,.0f})",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Location tier",yaxis_title="Employees",showlegend=False)
        c1.plotly_chart(fig,use_container_width=True);insight(f"Tier {top.label} contains {top.value:,.0f} employees in {dept}.")
    if not level.empty:
        top=level.sort_values("value",ascending=False).iloc[0]
        fig=px.bar(level,x="label",y="value",title=f"Level {top.label} is the largest group ({top.value:,.0f})",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Job level",yaxis_title="Employees",showlegend=False)
        c2.plotly_chart(fig,use_container_width=True);insight(f"Level {top.label} has the most employees in {dept}.")
    if not mode.empty:
        top=mode.sort_values("value",ascending=False).iloc[0]
        fig=px.bar(mode,x="label",y="value",title=f"{top.label} is the most common work mode ({top.value:,.0f})",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Work mode",yaxis_title="Employees",showlegend=False)
        st.plotly_chart(fig,use_container_width=True);insight(f"{top.label} is the most common work mode for {dept} ({top.value:,.0f}).")
elif user["role"] == "MANAGER":
    st.info("Demographic breakdowns are hidden in the manager persona.")

st.subheader("Five questions this page answers")
st.markdown("1. What is month-end headcount, and how is it changing?\n2. Which departments have the largest workforces?\n3. How many people joined or left in the selected month?\n4. Which location tier is largest?\n5. Which work mode is most common?")
st.caption("Filters use the governed metric layer. Minimum group sizes are enforced before demographic breakdowns are returned.")
