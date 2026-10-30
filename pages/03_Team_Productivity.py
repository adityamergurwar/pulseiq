import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, insight, query_df, require_user

st.title("Team productivity by sprint")
st.caption("Compare delivery patterns in context; story points alone are not a team performance score.")
st.markdown(
    "**Metric rules.** Velocity is the sum of story points on completed tasks per team and sprint. "
    "Cycle time is the average calendar days from start to completion for completed tasks. On-time rate is "
    "on-time completed tasks divided by all completed tasks. Completion is completed tasks divided by "
    "non-cancelled tasks. Cancelled tasks are excluded from completion and velocity; blocked work and "
    "reopen events remain visible as separate counts."
)
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role']=='EXECUTIVE': st.info("Team-level detail is hidden for the executive persona; use the company scorecard."); st.stop()
data=query_df("SELECT * FROM metrics.dashboard_task_operations ORDER BY sprint_id,team_id")
if user['role']=='MANAGER': data=data[data.team_id.astype(str)==str(user['team_id'])]
elif user['role']=='HR': data=data[data.department_id.astype(str)==str(user['department_id'])]
if data.empty: st.info("No team sprint rows are available for this role."); st.stop()
sprints=sorted(data.sprint_id.unique())
sprint=st.sidebar.selectbox("Sprint",sprints,index=len(sprints)-1)
frame=data[data.sprint_id==sprint].copy().sort_values("velocity",ascending=False)
if frame.empty: st.info("The selected sprint has no teams in scope."); st.stop()
team_options=frame.team_id.astype(str).tolist()
selected_team=st.sidebar.selectbox("Team",team_options)
row=frame[frame.team_id==selected_team].iloc[0]
k1,k2,k3,k4=st.columns(4)
k1.metric("Velocity",f"{float(row.velocity or 0):,.0f} points")
k2.metric("Cycle time",f"{float(row.cycle_time_days or 0):.1f} days")
k3.metric("On-time delivery",f"{float(row.on_time_pct or 0):.1f}%")
k4.metric("Completion",f"{float(row.completion_pct or 0):.1f}%")
b1,b2=st.columns(2)
b1.metric("Blocked tasks",f"{int(row.blocked_tasks):,}")
b2.metric("Reopen events",f"{int(row.reopened_count):,}")

top=frame.loc[frame.velocity.idxmax()]
fig=px.bar(frame.sort_values("velocity"),x="velocity",y="team_name",orientation="h",
  title=f"{top.team_name} has the highest velocity in {sprint} ({top.velocity:,.0f} points)",color_discrete_sequence=["#117C78"])
fig.update_layout(template="plotly_white",xaxis_title="Completed story points",yaxis_title=None)
st.plotly_chart(fig,use_container_width=True)
insight(f"{top.team_name} completed {top.velocity:,.0f} story points; velocity is not comparable across teams with different work mixes.")

fig=px.bar(frame.sort_values("overdue_tasks"),x="overdue_tasks",y="team_name",orientation="h",
  title=f"{frame.overdue_tasks.max():,.0f} overdue tasks is the sprint maximum",color_discrete_sequence=["#D17B0F"])
fig.update_layout(template="plotly_white",xaxis_title="Tasks overdue at data cutoff",yaxis_title=None)
st.plotly_chart(fig,use_container_width=True)
worst=frame.loc[frame.overdue_tasks.idxmax()]
insight(f"{worst.team_name} has {worst.overdue_tasks:,.0f} overdue tasks, {worst.blocked_tasks:,.0f} blocked tasks and {worst.reopened_count:,.0f} reopen events.")

fig=px.scatter(frame,x="cycle_time_days",y="on_time_pct",size="planned_tasks",hover_name="team_name",
  title="Cycle time and on-time delivery by team",color_discrete_sequence=["#117C78"])
fig.update_layout(template="plotly_white",xaxis_title="Average cycle time (days)",yaxis_title="On-time delivery (%)")
st.plotly_chart(fig,use_container_width=True)
best=frame.loc[frame.on_time_pct.idxmax()]
insight(f"{best.team_name} leads on-time delivery at {best.on_time_pct:.1f}% in {sprint}; each rate requires at least five completed tasks.")

comparison=frame[frame.team_id.isin(["T01","T02"])].set_index("team_id")
if {"T01","T02"}.issubset(comparison.index):
    platform,payments=comparison.loc["T01"],comparison.loc["T02"]
    st.info(
        f"Delivery-health comparison: Platform Core has {platform.velocity:,.0f} points, "
        f"{platform.on_time_pct:.1f}% on-time delivery and {platform.cycle_time_days:.2f}-day cycle time; "
        f"Payments & Billing has {payments.velocity:,.0f} points, {payments.on_time_pct:.1f}% on-time delivery "
        f"and {payments.cycle_time_days:.2f}-day cycle time. Platform Core recorded "
        f"{int(platform.reopened_count):,} reopen events and Payments & Billing recorded "
        f"{int(payments.reopened_count):,}; velocity alone does not establish which team is healthier."
    )

st.caption("The charts use governed M22–M25 metric views. Each team-sprint metric applies its dictionary minimum sample size.")
