import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, insight, money, query_df, require_user

st.title("Receivables, collections and cash")
st.caption("Invoice balances are reconstructed from dated payment events. Current open-status labels are not used to rewrite past periods.")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user = require_user()
if user["role"] not in {"ADMIN","EXECUTIVE"}:
    st.info("Client, receivable and cash details are limited to Admin and Executive roles.")
    st.stop()

asof = query_df("SELECT MAX(as_of_date) AS as_of_date FROM metrics.dashboard_receivables")
if asof.empty or pd.isna(asof.iloc[0, 0]):
    st.info("No issued invoice period is available.")
    st.stop()
report_date = pd.Timestamp(asof.iloc[0, 0]).date()
st.caption(f"Invoice reporting cut-off: {report_date:%d %b %Y}. Draft and cancelled invoices are excluded.")

receivables = query_df("SELECT * FROM metrics.dashboard_receivables ORDER BY balance DESC")
ageing = receivables.groupby("ageing_bucket", as_index=False).agg(balance=("balance", "sum"), invoices=("invoice_id", "nunique"))
total_open = float(receivables.balance.sum()) if not receivables.empty else 0.0
overdue = float(receivables.loc[receivables.ageing_bucket.isin(["1-30 days", "31-60 days", "61-90 days", "90+ days"]), "balance"].sum()) if not receivables.empty else 0.0
dso = query_df("SELECT value FROM metrics.m20_dso WHERE period=?", [report_date])
k1,k2,k3=st.columns(3)
k1.metric("Open receivables",money(total_open))
k2.metric("Past due",money(overdue))
k3.metric("Days sales outstanding",f"{float(dso.iloc[0,0]):.1f} days" if not dso.empty and pd.notna(dso.iloc[0,0]) else "Not available")

if not ageing.empty:
    order=["Not due","1-30 days","31-60 days","61-90 days","90+ days","Settled"]
    ageing["sort_order"]=ageing.ageing_bucket.map({v:i for i,v in enumerate(order)})
    ageing=ageing.sort_values("sort_order")
    fig=px.bar(ageing,x="ageing_bucket",y="balance",title=f"{money(overdue)} of {money(total_open)} open receivables are past due",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title="Age at report date",yaxis_title="Balance (INR)")
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(ageing.drop(columns="sort_order").style.format({"balance":"{:,.0f}"}),hide_index=True,use_container_width=True)
    insight(f"Ageing buckets sum to {money(ageing.balance.sum())}; the balance table uses invoice totals less payments received by {report_date:%d %b %Y}.")

cash=query_df("SELECT * FROM metrics.dashboard_cash_movement ORDER BY period")
if not cash.empty:
    fig=px.bar(cash,x="period",y=["cash_in","cash_out"],barmode="group",title="Cash movements show ledger cash-in and cash-out by month",color_discrete_sequence=["#117C78","#D17B0F"])
    fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Cash movement (INR)",legend_title=None)
    st.plotly_chart(fig,use_container_width=True)
    latest=cash.iloc[-1]
    st.metric("Closing cash movement balance",money(latest.closing_balance),f"as of {pd.Timestamp(latest.period):%b %Y}")
    insight(f"Account 1001 cumulative movement is {money(latest.closing_balance)}. No opening cash balance was supplied, so this is a movement-derived balance, not a bank statement balance.")

slow=query_df("SELECT client_name,average_days_to_pay,paid_invoices,open_receivables,average_days_open FROM metrics.dashboard_client_collection ORDER BY average_days_to_pay DESC") if user["role"]=="ADMIN" else pd.DataFrame()
if not slow.empty:
    slow=slow.head(10)
    fig=px.bar(slow.sort_values("average_days_to_pay"),x="average_days_to_pay",y="client_name",orientation="h",title=f"{slow.iloc[0].client_name} is the slowest payer among clients with five paid invoices",color_discrete_sequence=["#D17B0F"])
    fig.update_layout(template="plotly_white",xaxis_title="Average days to pay",yaxis_title=None)
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(slow,use_container_width=True,hide_index=True)
    insight(f"{slow.iloc[0].client_name} averages {slow.iloc[0].average_days_to_pay:.0f} days to pay across {slow.iloc[0].paid_invoices:,.0f} invoices; only client groups with at least five paid invoices are named.")

client_ar=query_df("SELECT client_name,overdue_balance,overdue_invoices,average_days_past_due FROM metrics.dashboard_overdue_by_client ORDER BY overdue_balance DESC LIMIT 10") if user["role"]=="ADMIN" else pd.DataFrame()
if not client_ar.empty:
    st.subheader("Largest grouped overdue clients")
    st.dataframe(client_ar.style.format({"overdue_balance":"{:,.0f}","average_days_past_due":"{:.0f}"}),hide_index=True,use_container_width=True)
