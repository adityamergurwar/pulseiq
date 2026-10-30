import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import department_picker, ensure_database, insight, money, query_df, require_user


st.title("Payroll cost and reconciliation")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] == "MANAGER":
    st.info("Payroll and salary information is not available to the manager persona.")
    st.stop()

department = department_picker(user)
st.caption(
    "Only company, department, and role aggregates are displayed. Groups below five people are suppressed; "
    "individual employee pay rows are not shown."
)

if department == "ALL":
    costs = query_df(
        "SELECT period,value FROM metrics.m09_payroll_cost WHERE department_id='ALL' ORDER BY 1"
    )
else:
    costs = query_df(
        "SELECT period,value FROM metrics.m09_payroll_cost WHERE department_id=? ORDER BY 1",
        [department],
    )
if costs.empty:
    st.info("No payroll data is available for this scope.")
    st.stop()

months = pd.to_datetime(costs.period).dt.date.tolist()
month = st.sidebar.selectbox("Payroll month", months, index=len(months) - 1)
cost = float(costs.loc[pd.to_datetime(costs.period).dt.date == month, "value"].iloc[0])
if department == "ALL":
    gross = query_df("SELECT value FROM metrics.m07_gross_pay WHERE department_id='ALL' AND period=?", [month])
    net = query_df("SELECT value FROM metrics.m08_net_pay WHERE department_id='ALL' AND period=?", [month])
    per_head = query_df("SELECT value FROM metrics.m10_cost_per_head WHERE department_id='ALL' AND period=?", [month])
    overtime = query_df("SELECT value FROM metrics.m11_overtime_share WHERE department_id='ALL' AND period=?", [month])
else:
    gross = query_df("SELECT value FROM metrics.m07_gross_pay WHERE department_id=? AND period=?", [department, month])
    net = query_df("SELECT value FROM metrics.m08_net_pay WHERE department_id=? AND period=?", [department, month])
    per_head = query_df("SELECT value FROM metrics.m10_cost_per_head WHERE department_id=? AND period=?", [department, month])
    overtime = query_df("SELECT value FROM metrics.m11_overtime_share WHERE department_id=? AND period=?", [department, month])

get_value = lambda frame: None if frame.empty else frame.iloc[0, 0]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Employer cost", money(cost))
k2.metric("Gross pay", money(get_value(gross)))
k3.metric("Net pay", money(get_value(net)))
k4.metric("Average cost per paid employee", money(get_value(per_head)))

fig = px.line(
    costs,
    x="period",
    y="value",
    markers=True,
    title=f"Employer payroll cost was {money(cost)} in {month:%b %Y}",
    color_discrete_sequence=["#117C78"],
)
fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Employer cost (INR)")
st.plotly_chart(fig, use_container_width=True)
peak = costs.loc[costs.value.idxmax()]
overtime_value = get_value(overtime)
insight(
    f"Payroll cost peaked at {money(peak.value)} in {peak.period:%b %Y}; "
    f"selected-month overtime share is {float(overtime_value or 0):.1f}%."
)

if user["role"] in {"ADMIN", "HR"}:
    roles = query_df(
        """SELECT role_title,COUNT(DISTINCT employee_id) AS employees,
                  SUM(gross_pay) AS gross_pay,SUM(net_pay) AS net_pay,
                  SUM(employer_cost) AS employer_cost,AVG(employer_cost) AS avg_employer_cost
           FROM metrics.dashboard_salary_detail
           WHERE period=? AND department_id=?
           GROUP BY 1 HAVING COUNT(DISTINCT employee_id)>=5 ORDER BY employer_cost DESC""",
        [month, department],
    )
    if not roles.empty:
        top = roles.iloc[0]
        fig = px.bar(
            roles.sort_values("employer_cost"),
            x="employer_cost",
            y="role_title",
            orientation="h",
            title=f"Highest grouped role cost: {top.role_title} ({money(top.employer_cost)})",
            color_discrete_sequence=["#117C78"],
        )
        fig.update_layout(template="plotly_white", xaxis_title="Employer cost (INR)", yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
        insight(
            f"{top.role_title} has the highest grouped employer cost at {money(top.employer_cost)} "
            f"across {top.employees:,.0f} paid employees; groups under five are hidden."
        )
        st.dataframe(roles, use_container_width=True, hide_index=True)
    else:
        st.info("No role group meets the minimum display size of five for this department and month.")
else:
    st.info("Role-level payroll detail is limited to HR and Admin, and is always shown as aggregates.")

st.subheader("Payroll exclusions and reasons")
latest_run = query_df("SELECT run_id FROM audit.etl_run_log ORDER BY started_at DESC LIMIT 1")
if not latest_run.empty:
    excluded = query_df(
        """SELECT source_row,reason FROM audit.quarantine
           WHERE run_id=? AND source_table='fact_payroll' ORDER BY source_row""",
        [latest_run.iloc[0, 0]],
    )
else:
    excluded = pd.DataFrame()
if not excluded.empty:
    excluded["reason"] = excluded.reason.str.replace(r"EMP-\d{4}", "employee identifier", regex=True)
    st.caption(
        "Four payroll rows were excluded after validation found duplicate employee/run keys or unmatched employee references. "
        "The raw source remains intact, and each excluded row is recorded with its source row and reason. "
        "The clean payroll output is reconciled against the reference months; employee IDs and pay amounts are omitted here."
    )
    st.dataframe(excluded, use_container_width=True, hide_index=True)
else:
    st.info("No payroll rows were quarantined in the latest ETL run.")

st.subheader("Clean payroll-to-ledger reconciliation")
reconciliation = query_df(
    "SELECT period,difference,status FROM audit.payroll_ledger_reconciliation_clean ORDER BY period"
)
if not reconciliation.empty:
    passed = int((reconciliation.status == "PASS").sum())
    largest_difference = float(reconciliation.difference.abs().max())
    r1, r2 = st.columns(2)
    r1.metric("Periods within INR 0.01", f"{passed} / {len(reconciliation)}")
    r2.metric("Largest absolute difference", money(largest_difference))
    st.dataframe(reconciliation, use_container_width=True, hide_index=True)
    st.caption(
        "The Phase 2 acceptance check also compares the clean payroll, ledger, cash, and receivables "
        "summaries against the PQ-09 reconciliation answer key."
    )
