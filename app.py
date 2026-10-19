"""PulseIQ workforce overview. All displayed measures come from metrics views."""
from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).with_name("pulseiq.duckdb")
st.set_page_config(page_title="PulseIQ | Workforce", page_icon="◉", layout="wide")
st.markdown("<style>.block-container{padding-top:2rem;max-width:1440px} h1{letter-spacing:-.04em}</style>", unsafe_allow_html=True)
st.title("PulseIQ · Workforce overview")
st.caption("Validated warehouse · fictional Zenith Nova workforce data")
if not DB.exists():
    st.warning("Build the warehouse first: run `python etl.py` from the project root.")
    st.stop()
con = duckdb.connect(str(DB), read_only=True)
dates = con.execute("SELECT DISTINCT month_start_date FROM metrics.m01_headcount ORDER BY 1").fetchdf()
departments = con.execute("SELECT DISTINCT department_id FROM metrics.dashboard_department_mix ORDER BY 1").fetchdf()
if dates.empty:
    st.info("No metric rows are available yet."); st.stop()
latest = pd.to_datetime(dates.iloc[-1, 0]).date()
department_options = ["All departments", *departments.department_id.tolist()]
left, right = st.columns([1, 2])
dept = left.selectbox("Department", department_options)
date_value = right.selectbox("Month", pd.to_datetime(dates.month_start_date).dt.date.tolist(), index=len(dates)-1)
where_dept = " AND department_id = ?"
selected_dept = "ALL" if dept == "All departments" else dept
params = [selected_dept]
trend = con.execute("SELECT month_start_date, SUM(value) headcount FROM metrics.m01_headcount WHERE month_start_date <= ?" + where_dept + " GROUP BY 1 ORDER BY 1", [date_value, *params]).fetchdf()
current = con.execute("SELECT SUM(value) FROM metrics.m01_headcount WHERE month_start_date=?" + where_dept, [date_value, *params]).fetchone()[0] or 0
prior = con.execute("SELECT SUM(value) FROM metrics.m01_headcount WHERE month_start_date=(SELECT MAX(month_start_date) FROM metrics.m01_headcount WHERE month_start_date<?)" + where_dept, [date_value, *params]).fetchone()[0] or 0
hires = con.execute("SELECT SUM(value) FROM metrics.m02_hires WHERE month_start_date=?" + where_dept, [date_value, *params]).fetchone()[0] or 0
exits = con.execute("SELECT SUM(value) FROM metrics.m03_exits WHERE month_start_date=?" + where_dept, [date_value, *params]).fetchone()[0] or 0
delta = ((current-prior)/prior*100) if prior else 0
k1,k2,k3,k4=st.columns(4)
k1.metric("Month end headcount", f"{current:,.0f}", f"{delta:+.1f}% vs prior month")
k2.metric("Hires", f"{hires:,.0f}", "during selected month")
k3.metric("Exits", f"{exits:,.0f}", "during selected month")
k4.metric("Net change", f"{hires-exits:+,.0f}", "hires less exits")

trend_title = f"Headcount {'grew' if delta >= 0 else 'fell'} {abs(delta):.1f}% to {current:,.0f} in {date_value:%b %Y}"
fig = px.line(trend, x="month_start_date", y="headcount", markers=True, title=trend_title, color_discrete_sequence=["#167D8D"])
fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Employees", margin=dict(l=10,r=10,t=55,b=5))
st.plotly_chart(fig, use_container_width=True)

if dept == "All departments":
    mix = con.execute("SELECT department_name label, value FROM metrics.dashboard_department_mix WHERE month_start_date=? ORDER BY value DESC", [date_value]).fetchdf()
else:
    mix = con.execute("SELECT department_name label, value FROM metrics.dashboard_department_mix WHERE department_id=? AND month_start_date=?", [dept,date_value]).fetchdf()
if not mix.empty:
    top = mix.iloc[0]
    c1,c2=st.columns(2)
    f=px.bar(mix.sort_values("value"),x="value",y="label",orientation="h",title=f"{top.label} is the largest department at {top.value:,.0f}",color_discrete_sequence=["#167D8D"])
    f.update_layout(template="plotly_white",xaxis_title="Employees",yaxis_title=None,showlegend=False,margin=dict(l=10,r=10,t=55,b=5))
    c1.plotly_chart(f,use_container_width=True)
    location=con.execute("SELECT label,value FROM metrics.dashboard_location_tier WHERE month_start_date=? AND department_id=? ORDER BY value DESC",[date_value,selected_dept]).fetchdf()
    if not location.empty:
        pxloc=px.bar(location,x="label",y="value",title=f"Tier {location.iloc[0].label} has the largest workforce ({location.iloc[0].value:,.0f})",color_discrete_sequence=["#167D8D"])
        pxloc.update_layout(template="plotly_white",xaxis_title="Location tier",yaxis_title="Employees",showlegend=False,margin=dict(l=10,r=10,t=55,b=5))
        c2.plotly_chart(pxloc,use_container_width=True)
    work=con.execute("SELECT label,value FROM metrics.dashboard_work_mode WHERE month_start_date=? AND department_id=? ORDER BY value DESC",[date_value,selected_dept]).fetchdf()
    if not work.empty:
        largest=work.iloc[0]
        fwork=px.bar(work,x="label",y="value",title=f"{largest.label} is the most common work mode ({largest.value:,.0f})",color_discrete_sequence=["#167D8D"])
        fwork.update_layout(template="plotly_white",xaxis_title="Work mode",yaxis_title="Employees",showlegend=False,margin=dict(l=10,r=10,t=55,b=5))
        st.plotly_chart(fwork,use_container_width=True)
st.caption(f"Selected month: {date_value:%d %b %Y} · Headcount history uses month-end warehouse snapshots.")
con.close()
