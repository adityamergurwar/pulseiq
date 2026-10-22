import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, insight, money, query_df, require_user

st.title("Profit and loss and operating expenses")
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role'] not in {'ADMIN','EXECUTIVE'}: st.info("Ledger and expense analytics are limited to Admin and Executive roles."); st.stop()
pnl=query_df("SELECT * FROM metrics.dashboard_pnl_monthly ORDER BY period")
if pnl.empty: st.info("No ledger period is available."); st.stop()
periods=pd.to_datetime(pnl.period).dt.date.tolist()
period=st.sidebar.selectbox("Month",periods,index=len(periods)-1)
row=pnl[pd.to_datetime(pnl.period).dt.date==period].iloc[0]
k1,k2,k3,k4=st.columns(4)
k1.metric("Revenue",money(row.revenue))
k2.metric("Operating expense",money(row.expenses))
k3.metric("Net profit",money(row.net_profit))
k4.metric("Operating margin",f"{row.operating_margin_pct:.1f}%")
st.caption(f"P&L tie: revenue {money(row.revenue)} + other income {money(row.other_income)} - expenses {money(row.expenses)} = net profit {money(row.net_profit)}; difference {money(row.reconciliation_difference)}.")
insight(f"Net profit was {money(row.net_profit)} in {period:%b %Y}, with a {row.operating_margin_pct:.1f}% margin.")

trend=pnl.copy()
fig=px.line(trend,x="period",y="net_profit",markers=True,title=f"Net profit peaked at {money(trend.net_profit.max())} in {trend.loc[trend.net_profit.idxmax(),'period']:%b %Y}",color_discrete_sequence=["#117C78"])
fig.update_layout(template="plotly_white",xaxis_title=None,yaxis_title="Net profit (INR)")
st.plotly_chart(fig,use_container_width=True)
insight(f"Across the period, the strongest month was {trend.loc[trend.net_profit.idxmax(),'period']:%b %Y}.")

expenses=query_df("SELECT account_name,SUM(spend) AS spend FROM metrics.dashboard_expense_category WHERE period=? GROUP BY 1 ORDER BY spend DESC",[period]) if user['role']=='ADMIN' else pd.DataFrame()
vendors=query_df("SELECT vendor_name,SUM(spend) AS spend FROM metrics.dashboard_vendor_spend WHERE period=? GROUP BY 1 ORDER BY spend DESC LIMIT 10",[period]) if user['role']=='ADMIN' else pd.DataFrame()
if user['role']=='EXECUTIVE': st.caption("Vendor and category detail is hidden for the executive persona; company P&L totals remain available.")
c1,c2=st.columns(2)
if not expenses.empty:
    top=expenses.iloc[0]
    fig=px.bar(expenses.sort_values("spend"),x="spend",y="account_name",orientation="h",title=f"{top.account_name} is the largest expense category ({money(top.spend)})",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title="Spend including GST (INR)",yaxis_title=None)
    c1.plotly_chart(fig,use_container_width=True)
    insight(f"{top.account_name} is the largest submitted-expense category at {money(top.spend)}.")
if not vendors.empty:
    top=vendors.iloc[0]
    fig=px.bar(vendors.sort_values("spend"),x="spend",y="vendor_name",orientation="h",title=f"{top.vendor_name} has the highest expense-vendor spend ({money(top.spend)})",color_discrete_sequence=["#117C78"])
    fig.update_layout(template="plotly_white",xaxis_title="Spend including GST (INR)",yaxis_title=None)
    c2.plotly_chart(fig,use_container_width=True)
    insight(f"{top.vendor_name} leads the expense register at {money(top.spend)} for the selected month.")
st.caption("P&L ledger expenses include accounts 5000–5999. Vendor/category visuals use the separate submitted-expense register and therefore need not equal ledger expense totals.")
