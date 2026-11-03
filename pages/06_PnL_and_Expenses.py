import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import ensure_database, insight, money, query_df, require_user


st.title("Profit and loss and operating expenses")
st.caption("Monthly results come from the posted ledger. Category and vendor detail comes from the submitted-expense register.")

if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] not in {"ADMIN", "EXECUTIVE"}:
    st.info("Ledger and expense analytics are limited to Admin and Executive personas.")
    st.stop()

pnl = query_df("SELECT * FROM metrics.dashboard_pnl_monthly ORDER BY period")
if pnl.empty:
    st.info("No ledger period is available.")
    st.stop()

periods = pd.to_datetime(pnl.period).dt.date.tolist()
period = st.sidebar.selectbox("Month", periods, index=len(periods) - 1)
row = pnl.loc[pd.to_datetime(pnl.period).dt.date == period].iloc[0]
period_index = periods.index(period)
prior = pnl.iloc[period_index - 1] if period_index > 0 else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Revenue", money(row.revenue))
k2.metric("Operating expense", money(row.expenses))
k3.metric("Net profit", money(row.net_profit))
k4.metric("Operating margin", f"{row.operating_margin_pct:.1f}%")

st.subheader(f"P&L statement · {period:%B %Y}")
statement = pd.DataFrame(
    [
        {"Line item": "Revenue", "Amount": money(row.revenue)},
        {"Line item": "Other income", "Amount": money(row.other_income)},
        {"Line item": "Operating expenses", "Amount": f"({money(row.expenses)})"},
        {"Line item": "Net profit", "Amount": money(row.net_profit)},
        {"Line item": "Operating margin", "Amount": f"{row.operating_margin_pct:.2f}%"},
    ]
)
st.dataframe(statement, use_container_width=True, hide_index=True)
st.caption(
    f"Tie-out: revenue {money(row.revenue)} + other income {money(row.other_income)} "
    f"- operating expenses {money(row.expenses)} = net profit {money(row.net_profit)}. "
    f"Difference: {money(row.reconciliation_difference)}. Only detail accounts are counted; group headings are excluded."
)
st.caption(
    "The source workbook README has no P&L amounts, so the 18-month headline baseline is documented in the project README. Monthly ledger totals are checked against the official reconciliation key and the accounting identity."
)

st.subheader("Revenue and expense trend")
trend = pnl.copy()
trend["period"] = pd.to_datetime(trend.period)
fig = px.line(
    trend,
    x="period",
    y=["revenue", "expenses"],
    markers=True,
    labels={"period": "Month", "value": "Amount (INR)", "variable": "Line"},
    color_discrete_map={"revenue": "#168F86", "expenses": "#D17B0F"},
)
fig.update_layout(template="plotly_white", legend_title=None, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

margin_fig = px.line(
    trend,
    x="period",
    y="operating_margin_pct",
    markers=True,
    labels={"period": "Month", "operating_margin_pct": "Operating margin (%)"},
    title="Operating margin by month",
    color_discrete_sequence=["#117C78"],
)
margin_fig.update_layout(template="plotly_white", yaxis_ticksuffix="%")
st.plotly_chart(margin_fig, use_container_width=True)

st.subheader("Three evidence-led explanations to test when margin falls")
if prior is None:
    st.info("A prior month is not available, so month-over-month margin drivers cannot be compared yet.")
else:
    revenue_change = float(row.revenue - prior.revenue)
    expense_change = float(row.expenses - prior.expenses)
    revenue_change_pct = 100 * revenue_change / prior.revenue if prior.revenue else None
    expense_change_pct = 100 * expense_change / prior.expenses if prior.expenses else None
    margin_change = float(row.operating_margin_pct - prior.operating_margin_pct)

    prior_period = pd.Timestamp(prior.period).date()
    account_mix = query_df(
        """SELECT period,account_code,account_name,amount
           FROM metrics.dashboard_pnl_account_mix
           WHERE account_type='INCOME' AND period IN (?,?)""",
        [prior_period, period],
    )
    mix_note = "Revenue detail accounts were stable or no prior-month mix data was available."
    if not account_mix.empty:
        account_mix["period"] = pd.to_datetime(account_mix.period).dt.date
        mix_wide = account_mix.pivot_table(
            index=["account_code", "account_name"], columns="period", values="amount", aggfunc="sum", fill_value=0
        )
        for comparison_period in (prior_period, period):
            if comparison_period not in mix_wide.columns:
                mix_wide[comparison_period] = 0.0
        prior_total = float(mix_wide[prior_period].sum())
        current_total = float(mix_wide[period].sum())
        mix_wide["prior_share"] = 100 * mix_wide[prior_period] / prior_total if prior_total else 0.0
        mix_wide["current_share"] = 100 * mix_wide[period] / current_total if current_total else 0.0
        mix_wide["share_change_pp"] = mix_wide["current_share"] - mix_wide["prior_share"]
        if len(mix_wide):
            mix_item = mix_wide.loc[mix_wide.share_change_pp.abs().idxmax()]
            mix_name = mix_item.name[1]
            mix_note = (
                f"{mix_name} shifted {mix_item.share_change_pp:+.1f} percentage points of recorded revenue "
                f"({mix_item.prior_share:.1f}% to {mix_item.current_share:.1f}%)."
            )

    payroll_rows = query_df(
        """SELECT period,value FROM metrics.m09_payroll_cost
           WHERE department_id='ALL' AND period IN (?,?) ORDER BY period""",
        [prior_period, period],
    )
    overtime_rows = query_df(
        """SELECT period,SUM(overtime_pay) AS overtime_pay
           FROM metrics.dashboard_department_impact WHERE period IN (?,?) GROUP BY 1 ORDER BY 1""",
        [prior_period, period],
    )
    payroll_note = "Payroll comparison is unavailable for this month pair."
    if len(payroll_rows) == 2:
        payroll_rows["period"] = pd.to_datetime(payroll_rows.period).dt.date
        payroll_prior = float(payroll_rows.loc[payroll_rows.period == prior_period, "value"].iloc[0])
        payroll_current = float(payroll_rows.loc[payroll_rows.period == period, "value"].iloc[0])
        overtime_prior = overtime_current = 0.0
        if not overtime_rows.empty:
            overtime_rows["period"] = pd.to_datetime(overtime_rows.period).dt.date
            overtime_prior = float(overtime_rows.loc[overtime_rows.period == prior_period, "overtime_pay"].sum())
            overtime_current = float(overtime_rows.loc[overtime_rows.period == period, "overtime_pay"].sum())
        payroll_note = (
            f"Employer payroll moved {money(payroll_current - payroll_prior)} "
            f"({money(payroll_prior)} to {money(payroll_current)}); overtime moved "
            f"{money(overtime_current - overtime_prior)}."
        )

    evidence_rows = [
        {
            "Possible cause": "Operating costs grew faster than revenue",
            "Evidence in this month pair": (
                f"Revenue {revenue_change_pct:+.1f}% ({money(revenue_change)}); expenses "
                f"{expense_change_pct:+.1f}% ({money(expense_change)}); margin {margin_change:+.2f} pp."
                if revenue_change_pct is not None and expense_change_pct is not None
                else "Revenue or expense base is zero; growth rates are not defined."
            ),
            "What would confirm it": "Review recurring versus one-off detail-account postings and invoice timing.",
        },
        {
            "Possible cause": "Revenue mix shifted toward lower-contribution work",
            "Evidence in this month pair": mix_note,
            "What would confirm it": "Compare price, volume and direct contribution margin by product, client or contract; account mix alone does not prove margin causation.",
        },
        {
            "Possible cause": "Staffing or overtime pressure increased people cost",
            "Evidence in this month pair": payroll_note,
            "What would confirm it": "Reconcile payroll postings to the ledger and review paid hours, vacancies, workload and utilization by department.",
        },
    ]
    st.caption("These are hypotheses to investigate, not causal claims. This month versus prior month: "
               f"{pd.Timestamp(period):%b %Y} versus {pd.Timestamp(prior_period):%b %Y}.")
    st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)

expenses = (
    query_df(
        """SELECT account_name, SUM(spend) AS spend
           FROM metrics.dashboard_expense_category
           WHERE period=? GROUP BY 1 ORDER BY spend DESC""",
        [period],
    )
    if user["role"] == "ADMIN"
    else pd.DataFrame()
)
vendors = (
    query_df(
        """SELECT vendor_name, SUM(spend) AS spend
           FROM metrics.dashboard_vendor_spend
           WHERE period=? GROUP BY 1 ORDER BY spend DESC LIMIT 10""",
        [period],
    )
    if user["role"] == "ADMIN"
    else pd.DataFrame()
)

st.subheader("Submitted expenses by category and vendor")
if user["role"] == "EXECUTIVE":
    st.caption("Vendor and category detail is hidden for this persona; company ledger totals remain available.")
else:
    st.caption("Category and vendor spend includes GST and reflects the submitted-expense register, not the ledger P&L subtotal.")
    left, right = st.columns(2)
    if not expenses.empty:
        category_chart = px.bar(
            expenses.sort_values("spend"),
            x="spend",
            y="account_name",
            orientation="h",
            title="Expense register by category",
            color_discrete_sequence=["#117C78"],
        )
        category_chart.update_layout(template="plotly_white", xaxis_title="Submitted spend incl. GST (INR)", yaxis_title=None)
        left.plotly_chart(category_chart, use_container_width=True)
    if not vendors.empty:
        vendor_chart = px.bar(
            vendors.sort_values("spend"),
            x="spend",
            y="vendor_name",
            orientation="h",
            title="Top 10 expense vendors",
            color_discrete_sequence=["#D17B0F"],
        )
        vendor_chart.update_layout(template="plotly_white", xaxis_title="Submitted spend incl. GST (INR)", yaxis_title=None)
        right.plotly_chart(vendor_chart, use_container_width=True)

    st.subheader("Three monthly findings")
    period_rows = trend.sort_values("period").reset_index(drop=True)
    margin_change = row.operating_margin_pct - prior.operating_margin_pct if prior is not None else None
    if margin_change is None:
        margin_text = f"Operating margin was {row.operating_margin_pct:.1f}% in {period:%b %Y}; this is the first available month."
    else:
        direction = "increased" if margin_change >= 0 else "decreased"
        margin_text = f"Operating margin {direction} by {abs(margin_change):.1f} percentage points to {row.operating_margin_pct:.1f}% in {period:%b %Y}."
    st.markdown(f"- {margin_text}")
    if not expenses.empty and not vendors.empty:
        category_total = float(expenses.spend.sum())
        vendor_total = float(vendors.spend.sum())
        top_category = expenses.iloc[0]
        top_vendor = vendors.iloc[0]
        vendor_share = 100 * float(top_vendor.spend) / vendor_total if vendor_total else 0
        st.markdown(
            f"- **{top_category.account_name}** was the largest submitted-expense category at {money(top_category.spend)}."
        )
        st.markdown(
            f"- **{top_vendor.vendor_name}** led the top-10 vendor list at {money(top_vendor.spend)} "
            f"({vendor_share:.1f}% of top-10 vendor spend); those vendors total {money(vendor_total)}."
        )
