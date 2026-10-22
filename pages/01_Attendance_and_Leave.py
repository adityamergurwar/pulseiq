import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, pct, query_df, require_user

st.title("Attendance and leave trends")
st.caption("Attendance uses scheduled days; approved leave is shown separately. Weekend and holiday dates come from the date dimension.")
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role']=='MANAGER': st.info("This page contains department-wide attendance and leave details. The manager persona is restricted to team productivity."); st.stop()
dept=department_picker(user)
dept_frame=query_df("SELECT DISTINCT period FROM metrics.m13_attendance_rate WHERE department_id=? ORDER BY 1",[dept])
if dept_frame.empty: st.info("No attendance metrics are available for this scope."); st.stop()
periods=pd.to_datetime(dept_frame.period).dt.date.tolist()
start=st.sidebar.selectbox("Start month",periods,max(0,len(periods)-12),key="attendance_start")
attendance=query_df("SELECT period,value AS rate FROM metrics.m13_attendance_rate WHERE department_id=? AND period>=? ORDER BY 1",[dept,start])
late=query_df("SELECT period,100.0*value AS rate FROM metrics.m14_late_arrival_rate WHERE department_id=? AND period>=? ORDER BY 1",[dept,start])
overtime=query_df("SELECT period,value AS rate FROM metrics.m11_overtime_share WHERE department_id=? AND period>=? ORDER BY 1",[dept,start])
leaves=query_df("SELECT period,SUM(leave_days) AS leave_days FROM metrics.dashboard_leave_monthly WHERE department_id=? AND period>=? GROUP BY 1 ORDER BY 1",[dept,start])
holiday=query_df("SELECT period,holiday_group,requests FROM metrics.dashboard_leave_holiday WHERE department_id=? ORDER BY 1,2",[dept])
k1,k2,k3=st.columns(3)
if not attendance.empty: k1.metric("Latest attendance",pct(attendance.rate.iloc[-1],False))
if not late.empty: k2.metric("Latest late-arrival rate",pct(late.rate.iloc[-1]))
if not overtime.empty: k3.metric("Latest overtime share",pct(overtime.rate.iloc[-1]))

if not attendance.empty:
    fig=px.line(attendance,x="period",y="rate",markers=True,title=f"Attendance was {pct(attendance.rate.iloc[-1],False)} in {attendance.period.iloc[-1]:%b %Y}",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",yaxis_tickformat=".0%",yaxis_title="Attendance rate",xaxis_title=None)
    st.plotly_chart(fig,use_container_width=True)
    bottom=attendance.nsmallest(1,"rate").iloc[0]
    insight(f"The lowest month in the selected range was {bottom.period:%b %Y} at {pct(bottom.rate,False)}.")
if not leaves.empty:
    fig=px.bar(leaves,x="period",y="leave_days",title=f"Approved leave peaked at {leaves.leave_days.max():,.0f} days in {leaves.loc[leaves.leave_days.idxmax(),'period']:%b %Y}",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Approved leave days")
    st.plotly_chart(fig,use_container_width=True)
    peak=leaves.loc[leaves.leave_days.idxmax()]
    insight(f"Approved leave reached {peak.leave_days:,.0f} days in {peak.period:%b %Y} for {dept}.")
c1,c2=st.columns(2)
if not late.empty:
    fig=px.line(late,x="period",y="rate",markers=True,title=f"Late arrivals peaked at {late.rate.max():.1f}% of present days",color_discrete_sequence=["#D17B0F"])
    fig.update_layout(template="plotly_white",yaxis_title="Late arrivals / present days (%)",xaxis_title=None)
    c1.plotly_chart(fig,use_container_width=True)
    peak=late.loc[late.rate.idxmax()]
    insight(f"Late arrivals peaked at {peak.rate:.1f}% in {peak.period:%b %Y}.")
if not overtime.empty:
    fig=px.line(overtime,x="period",y="rate",markers=True,title=f"Overtime share peaked at {overtime.rate.max():.1f}% of payroll cost",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",yaxis_title="Overtime share (%)",xaxis_title=None)
    c2.plotly_chart(fig,use_container_width=True)
    peak=overtime.loc[overtime.rate.idxmax()]
    insight(f"Overtime share reached {peak.rate:.1f}% in {peak.period:%b %Y}.")
if not holiday.empty:
    fig=px.bar(holiday,x="period",y="requests",color="holiday_group",barmode="group",title="Approved leave requests are grouped by whether their date range overlaps a public holiday")
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Leave requests",legend_title=None)
    st.plotly_chart(fig,use_container_width=True)
    peak=holiday.groupby("holiday_group",as_index=False).requests.sum().sort_values("requests",ascending=False)
    insight(f"The larger holiday-overlap category is {peak.iloc[0].holiday_group.lower()} with {peak.iloc[0].requests:,.0f} requests in the selected scope.")
    st.dataframe(holiday,use_container_width=True,hide_index=True)
