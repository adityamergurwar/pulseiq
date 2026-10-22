import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, money, query_df, require_user

st.title("Payroll cost")
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role']=='MANAGER': st.info("Payroll and salary-level information is not available to the manager persona."); st.stop()
dept=department_picker(user)
if user['role']=='EXECUTIVE':
    st.caption("Company-level payroll cost only. Salary details are hidden for this role.")
else:
    st.caption("Employee-level amounts are shown only to ADMIN and HR personas. HR is scoped to its assigned department.")
costs=query_df("SELECT period,value FROM metrics.m09_payroll_cost WHERE department_id=? ORDER BY 1",[dept])
if costs.empty: st.info("No payroll data is available for this scope."); st.stop()
periods=pd.to_datetime(costs.period).dt.date.tolist()
period=st.sidebar.selectbox("Payroll month",periods,index=len(periods)-1)
cost=float(costs.loc[pd.to_datetime(costs.period).dt.date==period,'value'].iloc[0])
if dept=='ALL':
    gross=query_df("SELECT value FROM metrics.m07_gross_pay WHERE department_id='ALL' AND period=?",[period])
    net=query_df("SELECT value FROM metrics.m08_net_pay WHERE department_id='ALL' AND period=?",[period])
    perhead=query_df("SELECT value FROM metrics.m10_cost_per_head WHERE department_id='ALL' AND period=?",[period])
    overtime=query_df("SELECT value FROM metrics.m11_overtime_share WHERE department_id='ALL' AND period=?",[period])
else:
    gross=query_df("SELECT value FROM metrics.m07_gross_pay WHERE department_id=? AND period=?",[dept,period])
    net=query_df("SELECT value FROM metrics.m08_net_pay WHERE department_id=? AND period=?",[dept,period])
    perhead=query_df("SELECT value FROM metrics.m10_cost_per_head WHERE department_id=? AND period=?",[dept,period])
    overtime=query_df("SELECT value FROM metrics.m11_overtime_share WHERE department_id=? AND period=?",[dept,period])
get=lambda df: None if df.empty else df.iloc[0,0]
k1,k2,k3,k4=st.columns(4)
k1.metric("Employer cost",money(cost))
k2.metric("Gross pay",money(get(gross)))
k3.metric("Net pay",money(get(net)))
k4.metric("Cost per paid employee",money(get(perhead)))

fig=px.line(costs,x="period",y="value",markers=True,title=f"Payroll cost was {money(cost)} in {period:%b %Y}",color_discrete_sequence=["#117C78"])
fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Employer cost (INR)")
st.plotly_chart(fig,use_container_width=True)
peak=costs.loc[costs.value.idxmax()]
insight(f"Payroll cost peaked at {money(peak.value)} in {peak.period:%b %Y}; selected month overtime share is {float(get(overtime) or 0):.1f}%.")

if user['role'] in {'ADMIN','HR'}:
    roles=query_df("""SELECT role_title,COUNT(DISTINCT employee_id) AS employees,
                       SUM(gross_pay) AS gross_pay,SUM(net_pay) AS net_pay,SUM(employer_cost) AS employer_cost
                    FROM metrics.dashboard_salary_detail WHERE period=? AND department_id=?
                    GROUP BY 1 HAVING COUNT(DISTINCT employee_id)>=5 ORDER BY employer_cost DESC""",[period,dept])
    if not roles.empty:
        top=roles.iloc[0]
        fig=px.bar(roles.sort_values('employer_cost'),x='employer_cost',y='role_title',orientation='h',
                   title=f"{top.role_title} has the highest grouped employer cost ({money(top.employer_cost)})",
                   color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title="Employer cost (INR)",yaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
        insight(f"{top.role_title} leads grouped payroll cost at {money(top.employer_cost)} across {top.employees:,.0f} paid employees; groups under five are hidden.")
        st.dataframe(roles,use_container_width=True,hide_index=True)
    detail=query_df("SELECT period,employee_id,role_title,gross_pay,net_pay,employer_cost FROM metrics.dashboard_salary_detail WHERE period=? AND department_id=? ORDER BY employer_cost DESC",[period,dept])
    st.subheader("Salary-level detail | restricted demo view")
    st.caption("No employee names are shown. In production, turn on PULSEIQ_REQUIRE_LOGIN and set secret-backed role scopes before deployment.")
    st.dataframe(detail,use_container_width=True,hide_index=True)
else:
    st.info("Salary-level detail is not returned for the executive persona.")
