import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, insight, query_df, require_user

st.title("Team productivity by sprint")
st.caption("Cancelled tasks are excluded from completion. Invalid task dates are quarantined and listed in Data Quality.")
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

st.caption("The charts use governed M22–M25 metric views. Canceled tasks do not contribute to completion or velocity.")
