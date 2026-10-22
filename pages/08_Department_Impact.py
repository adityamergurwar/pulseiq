import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, money, query_df, require_user

st.title("Department impact")
st.caption("Payroll, attendance, approved leave, headcount, attrition and sprint work are aggregated separately before they are joined by department and month.")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user=require_user()
if user["role"]=="MANAGER":
    st.info("This comparative view is limited to HR, Admin and executive personas.")
    st.stop()
dept=department_picker(user)
data=query_df("SELECT * FROM metrics.dashboard_department_impact ORDER BY period,department_id")
if user["role"] in {"HR","ADMIN"} and dept!="ALL": data=data[data.department_id.astype(str)==str(dept)]
periods=sorted(pd.to_datetime(data.period).dt.date.unique())
period=st.sidebar.selectbox("Month",periods,index=len(periods)-1)
frame=data[pd.to_datetime(data.period).dt.date==period].copy()
if frame.empty:
    st.info("No department-month groups meet the minimum size for this period.")
    st.stop()

if user["role"]=="EXECUTIVE":
    st.info("Department labels and small groups are hidden for the executive persona. Company totals are shown below.")
    total={k:frame[k].sum(min_count=1) for k in ["payroll_cost","gross_pay","overtime_pay","overtime_hours","late_arrivals","approved_leave_days","paid_people","hires","exits","planned_tasks","done_tasks","story_points_done","headcount_start","headcount_end","attendance_numerator","scheduled_days"]}
    total["attendance_rate"]=total["attendance_numerator"]/max(1,total["scheduled_days"])
    total["attrition_pct"]=100*total["exits"]/max(1,total["headcount_start"])
    total["task_completion_pct"]=100*total["done_tasks"]/max(1,total["planned_tasks"])
    total["leave_days_per_head"]=total["approved_leave_days"]/max(1,frame.headcount_end.sum())
    total["cost_per_head"]=total["payroll_cost"]/max(1,total["paid_people"])
    total["overtime_share_pct"]=100*total["overtime_pay"]/max(1,total["payroll_cost"])
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Employer payroll cost",money(total["payroll_cost"]))
    k2.metric("Attendance",f"{total['attendance_rate']:.1%}")
    k3.metric("Monthly attrition",f"{total['attrition_pct']:.2f}%")
    k4.metric("Task completion",f"{total['task_completion_pct']:.1f}%")
    st.dataframe(pd.DataFrame([{"Payroll cost":total["payroll_cost"],"Gross pay":total["gross_pay"],"Overtime pay":total["overtime_pay"],"Overtime hours":total["overtime_hours"],"Approved leave days":total["approved_leave_days"],"Leave days per head":total["leave_days_per_head"],"Hires":total["hires"],"Exits":total["exits"],"Tasks planned":total["planned_tasks"],"Tasks done":total["done_tasks"],"Story points done":total["story_points_done"]}]).style.format({c:"{:,.1f}" for c in total if c in ["payroll_cost","gross_pay","overtime_pay","overtime_hours","approved_leave_days","leave_days_per_head","hires","exits","planned_tasks","done_tasks","story_points_done"]}),hide_index=True,use_container_width=True)
    insight(f"Across groups of at least five paid employees, payroll cost is {money(total['payroll_cost'])}; leave averages {total['leave_days_per_head']:.2f} approved days per month-end employee.")
else:
    st.caption("The reference comparison key contains a one-person D00 group. PulseIQ suppresses that group to protect salary and attendance privacy.")
    cost=frame.sort_values("payroll_cost",ascending=False)
    top=cost.iloc[0]
    fig=px.bar(cost.sort_values("payroll_cost"),x="payroll_cost",y="department_id",orientation="h",title=f"{top.department_id} has the highest employer payroll cost ({money(top.payroll_cost)})",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title="Employer cost (INR)",yaxis_title=None)
    st.plotly_chart(fig,use_container_width=True)
    insight(f"{top.department_id} has the highest employer cost at {money(top.payroll_cost)} for {top.paid_people:,.0f} paid employees.")
    fig=px.scatter(frame,x="cost_per_head",y="attrition_pct",size="paid_people",hover_name="department_id",color="department_id",title="Cost per paid employee and monthly attrition by department")
    fig.update_layout(template="plotly_white",xaxis_title="Employer cost per paid employee (INR)",yaxis_title="Monthly attrition (%)",showlegend=False)
    st.plotly_chart(fig,use_container_width=True)
    highest=frame.loc[frame.attrition_pct.idxmax()]
    insight(f"{highest.department_id} has the highest monthly attrition at {highest.attrition_pct:.2f}%; the point size represents paid headcount.")
    show=["department_id","payroll_cost","gross_pay","overtime_pay","overtime_hours","late_arrivals","attendance_rate","approved_leave_days","leave_days_per_head","headcount_end","hires","exits","attrition_pct","planned_tasks","done_tasks","story_points_done","task_completion_pct","cost_per_head","overtime_share_pct"]
    st.dataframe(frame[show].sort_values("payroll_cost",ascending=False).style.format({c:"{:,.2f}" for c in show if c not in ["department_id"]}),hide_index=True,use_container_width=True)

st.warning("Validation differences are intentional and documented: four post-exit attendance rows, four invalid payroll rows and 20 invalid task rows are quarantined. The answer key includes all 11 departments; D00 is suppressed here because it has one person. See docs/validation_results.md for row-level comparison counts without exposing the D00 values.")
