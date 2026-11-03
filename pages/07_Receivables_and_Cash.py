import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import ensure_database, insight, money, query_df, require_user


st.title("Receivables, collections and cash")
st.caption("Open invoices are SENT, OVERDUE or PARTIALLY_PAID. Draft, cancelled and paid invoices are excluded from current open receivables.")

if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] not in {"ADMIN", "EXECUTIVE"}:
    st.info("Client, receivable and cash detail is limited to Admin and Executive personas.")
    st.stop()

receivables = query_df("SELECT * FROM metrics.dashboard_receivables ORDER BY balance DESC")
if receivables.empty:
    st.info("No open invoices are available at the latest reporting date.")
    st.stop()

report_date = pd.Timestamp(receivables.as_of_date.max()).date()
period = pd.Timestamp(receivables.period.max()).date()
st.caption(f"Open receivables as at {report_date:%d %b %Y}. Ageing is measured from due date; not-due balances are shown separately.")

total_open = float(receivables.balance.sum())
overdue = float(receivables.loc[receivables.ageing_bucket != "Not due", "balance"].sum())
dso = query_df("SELECT value FROM metrics.m20_dso WHERE period=?", [report_date])
k1, k2, k3 = st.columns(3)
k1.metric("Open receivables", money(total_open))
k2.metric("Past due", money(overdue))
k3.metric(
    "Days sales outstanding",
    f"{float(dso.iloc[0, 0]):.1f} days" if not dso.empty and pd.notna(dso.iloc[0, 0]) else "Not available",
)

bucket_order = ["Not due", "0-30 days", "31-60 days", "61-90 days", "90+ days"]
ageing = (
    receivables.groupby("ageing_bucket", as_index=False)
    .agg(balance=("balance", "sum"), invoices=("invoice_id", "nunique"))
)
ageing = pd.DataFrame({"ageing_bucket": bucket_order}).merge(ageing, on="ageing_bucket", how="left")
ageing[["balance", "invoices"]] = ageing[["balance", "invoices"]].fillna(0)
bucket_total = float(ageing.balance.sum())
reconciliation_difference = bucket_total - total_open

st.subheader("Open receivables ageing")
fig = px.bar(
    ageing,
    x="ageing_bucket",
    y="balance",
    title=f"{money(overdue)} of {money(total_open)} is past due",
    color_discrete_sequence=["#117C78"],
    category_orders={"ageing_bucket": bucket_order},
)
fig.update_layout(template="plotly_white", xaxis_title="Age at report date", yaxis_title="Balance (INR)")
st.plotly_chart(fig, use_container_width=True)
st.dataframe(ageing.style.format({"balance": "INR {:,.0f}", "invoices": "{:,.0f}"}), hide_index=True, use_container_width=True)
if abs(reconciliation_difference) <= 0.01:
    st.success(f"Bucket check passed: {money(bucket_total)} across all buckets equals total open receivables ({money(total_open)}).")
else:
    st.error(f"Bucket check failed by {money(reconciliation_difference)}.")
insight("Age buckets are 0-30, 31-60, 61-90 and 90+ days past due; not-due balances are a separate bucket.")

cash = query_df("SELECT * FROM metrics.dashboard_cash_movement ORDER BY period")
if not cash.empty:
    st.subheader("Cash in versus cash out")
    cash_chart = px.bar(
        cash,
        x="period",
        y=["cash_in", "cash_out"],
        barmode="group",
        labels={"period": "Month", "value": "Cash movement (INR)", "variable": "Movement"},
        color_discrete_map={"cash_in": "#168F86", "cash_out": "#D17B0F"},
    )
    cash_chart.update_layout(template="plotly_white", legend_title=None, hovermode="x unified")
    st.plotly_chart(cash_chart, use_container_width=True)
    latest = cash.iloc[-1]
    st.caption(
        f"The ledger shows cumulative net movement of {money(latest.closing_balance)} through "
        f"{pd.Timestamp(latest.period):%b %Y}. No opening bank balance was supplied, so this is not a bank statement balance."
    )

slow = (
    query_df(
        """SELECT client_name, average_days_to_pay, paid_invoices, open_receivables
           FROM metrics.dashboard_client_collection
           ORDER BY average_days_to_pay DESC"""
    )
    if user["role"] == "ADMIN"
    else pd.DataFrame()
)
if not slow.empty:
    st.subheader("Slowest-paying clients")
    slow_chart = px.bar(
        slow.sort_values("average_days_to_pay"),
        x="average_days_to_pay",
        y="client_name",
        orientation="h",
        title="Average payment days by client",
        color_discrete_sequence=["#D17B0F"],
    )
    slow_chart.update_layout(template="plotly_white", xaxis_title="Average days to pay", yaxis_title=None)
    st.plotly_chart(slow_chart, use_container_width=True)
    st.dataframe(slow, hide_index=True, use_container_width=True)
    top_slow = slow.sort_values("average_days_to_pay", ascending=False).iloc[0]
    insight(
        f"{top_slow.client_name} averages {top_slow.average_days_to_pay:.0f} days to pay "
        f"across {top_slow.paid_invoices:,.0f} paid invoices. Compare this pattern with contracted terms before escalating."
    )

st.subheader("How to assess a 75-day payer")
st.caption(
    "A 75-day average is a cash-planning risk when it exceeds agreed terms or clusters in overdue balances; it is not automatically late if the contract allows 75 days. "
    "Ask Finance to confirm the contractual due date, dispute or credit-note status, promised receipt date, client concentration, and whether the open invoices are already past due. "
    "Use the invoice count beside each average to judge how much history supports it."
)

overdue_clients = (
    query_df(
        """SELECT client_name, overdue_balance, overdue_invoices, average_days_past_due
           FROM metrics.dashboard_overdue_by_client
           WHERE as_of_date=? ORDER BY overdue_balance DESC LIMIT 10""",
        [report_date],
    )
    if user["role"] == "ADMIN"
    else pd.DataFrame()
)
if not overdue_clients.empty:
    st.subheader("Clients with the most overdue money")
    overdue_clients = overdue_clients.style.format(
        {"overdue_balance": "{:,.0f}", "average_days_past_due": "{:.0f}"}
    )
    st.dataframe(overdue_clients, hide_index=True, use_container_width=True)
elif user["role"] == "ADMIN":
    st.info("No open client balance is past due at this reporting date.")
