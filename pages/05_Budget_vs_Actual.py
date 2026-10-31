import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pulseiq.app_common import DB_PATH, department_picker, ensure_database, insight, money, query_df, require_user

st.title("Payroll budget versus actual")
if not ensure_database(): st.warning("Run python etl.py first."); st.stop()
user=require_user()
if user['role'] not in {'ADMIN','EXECUTIVE'}: st.info("Budget and finance targets are limited to Admin and Executive roles."); st.stop()
dept=department_picker(user)
data=query_df("SELECT * FROM metrics.dashboard_budget_actuals ORDER BY period,department_id")
if user['role'] in {'HR','ADMIN'} and dept!='ALL': data=data[data.department_id.astype(str)==str(dept)]
months=sorted(pd.to_datetime(data.period).dt.date.unique())
month=st.sidebar.selectbox("Budget month",months,index=len(months)-1)
frame=data[pd.to_datetime(data.period).dt.date==month].copy()
if frame.empty: st.info("No budget rows are available for this month."); st.stop()
if user['role']=='EXECUTIVE':
    total=pd.DataFrame([{"department_id":"Company","budget_cost":frame.budget_cost.sum(),"actual_cost":frame.actual_cost.sum(),"variance":frame.variance.sum(),"variance_pct":100*frame.variance.sum()/frame.budget_cost.sum(),"status":"RED" if frame.variance.sum()>frame.budget_cost.sum()*.05 else ("AMBER" if frame.variance.sum()>0 else "GREEN"),"recommendation":"Review the largest department variances shown in the executive summary."}])
    display=total
else:
    display=frame.copy()
display=display.sort_values("variance",ascending=False)
def status_color(value):
    colors={"GREEN":"#DFF2E2;color:#14532D","AMBER":"#FFF1CC;color:#713F12","RED":"#FEE2E2;color:#7F1D1D","NO DATA":"#E5E7EB;color:#374151"}
    return colors.get(str(value),"")
top=display.iloc[0]
k1,k2,k3=st.columns(3)
k1.metric("Budget",money(display.budget_cost.sum()))
k2.metric("Actual",money(display.actual_cost.sum()))
k3.metric("Variance",money(display.variance.sum()),f"{100*display.variance.sum()/display.budget_cost.sum():+.1f}%")
plot_df=display.sort_values("variance").copy()
variance=plot_df.variance.astype(float)
departments=plot_df.department_id.astype(str).tolist()
labels=[f"{value / 1000:+,.1f}k" if abs(value)>=1000 else f"{value:+,.0f}" for value in variance]
custom_values=variance.abs().tolist()
low=min(0.0,float(variance.min()))
high=max(0.0,float(variance.max()))
extent=max(abs(low),abs(high),1.0)*1.2
fig=go.Figure()
fig.add_trace(go.Bar(
    name="Overspend",
    x=variance.clip(lower=0).tolist(),
    y=departments,
    orientation="h",
    marker_color="#E58A1F",
    text=[label if value>0 else "" for label,value in zip(labels,variance)],
    textposition="outside",
    textfont={"size":10,"color":"#F3F4F6"},
    customdata=custom_values,
    cliponaxis=False,
    hovertemplate="<b>%{y}</b><br>INR %{customdata:,.0f} over budget<extra></extra>",
))
fig.add_trace(go.Bar(
    name="Under budget",
    x=variance.clip(upper=0).tolist(),
    y=departments,
    orientation="h",
    marker_color="#168F86",
    text=[label if value<0 else "" for label,value in zip(labels,variance)],
    textposition="outside",
    textfont={"size":10,"color":"#F3F4F6"},
    customdata=custom_values,
    cliponaxis=False,
    hovertemplate="<b>%{y}</b><br>INR %{customdata:,.0f} under budget<extra></extra>",
))
fig.update_layout(
    template="plotly_dark",
    title={"text":"Department variance (actual - budget)","x":0.01,"xanchor":"left","font":{"size":16}},
    barmode="overlay",
    height=470,
    margin={"l":18,"r":78,"t":82,"b":58},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"family":"Arial, sans-serif","size":12,"color":"#E5E7EB"},
    legend={"orientation":"h","x":1,"xanchor":"right","y":1.12,"yanchor":"bottom","font":{"size":10}},
    hoverlabel={"bgcolor":"#111827","font":{"color":"#F9FAFB"}},
    xaxis={
        "title":"Variance (INR)","tickformat":"~s","showgrid":True,
        "gridcolor":"rgba(148,163,184,0.20)","zeroline":True,
        "zerolinecolor":"#9CA3AF","zerolinewidth":2,
        "range":[-extent,extent],"tickfont":{"size":10},
    },
    yaxis={
        "title":None,"categoryorder":"array","categoryarray":departments,
        "showgrid":False,"tickfont":{"size":11},
    },
)
st.plotly_chart(fig,use_container_width=True,theme=None)
insight(f"{top.department_id} ranks first for overspend in {month:%b %Y}, with {money(top.variance)} variance.")
budget_table=display[["department_id","budget_cost","actual_cost","variance","variance_pct","status","recommendation"]].style.format({"budget_cost":"{:,.0f}","actual_cost":"{:,.0f}","variance":"{:,.0f}","variance_pct":"{:+.1f}%"}).map(status_color,subset=["status"])
st.dataframe(budget_table,use_container_width=True,hide_index=True)
over=display[display.variance>0].head(2)
st.subheader("Recommended actions for the largest overspends")
if over.empty:
    st.success("No department is over budget in the selected month.")
else:
    for _,row in over.iterrows():
        st.markdown(f"- **{row.department_id} ({money(row.variance)}):** {row.recommendation}")
st.caption("Status uses green when at or under budget, amber up to 5% over, and red above 5%. These are operating thresholds, not source targets.")
st.caption("Variance = actual payroll cost − budget. A positive amount is an overspend; a negative amount is underspend.")
st.caption("Budget values are the approved baseline in the supplied snapshot. If a hiring freeze or other plan change makes that baseline stale, show the gap and review a revised scenario before interpreting the variance.")

st.subheader("KPI status against approved monthly targets")
targets=query_df("SELECT period,department_id,metric,target_value,actual_value,direction,status,variance,sample_size FROM metrics.dashboard_kpi_targets WHERE period=? ORDER BY metric,department_id",[month])
if user['role']=='HR': targets=targets[targets.department_id.astype(str)==str(dept)]
elif user['role']=='ADMIN' and dept!='ALL': targets=targets[targets.department_id.astype(str)==str(dept)]
elif user['role']=='EXECUTIVE':
    target_map={r.metric:float(r.target_value) for _,r in query_df("SELECT metric,AVG(target_value) target_value FROM metrics.dashboard_kpi_targets WHERE period=? GROUP BY 1",[month]).iterrows()}
    all_metrics={
      'Attendance rate':('SELECT 100*value FROM metrics.m13_attendance_rate WHERE period=? AND department_id=\'ALL\'',[month]),
      'Overtime share':('SELECT value FROM metrics.m11_overtime_share WHERE period=? AND department_id=\'ALL\'',[month]),
      'Monthly attrition':('SELECT value FROM metrics.m04_attrition_monthly WHERE period=? AND department_id=\'ALL\'',[month]),
      'Task completion':('SELECT value FROM metrics.dashboard_task_completion_monthly WHERE period=? AND department_id=\'ALL\'',[month]),
    }
    rows=[]
    for name,(sql,params) in all_metrics.items():
        actual_df=query_df(sql,params); actual=float(actual_df.iloc[0,0]) if not actual_df.empty else None
        target=target_map.get(name); direction='Higher is better' if name in {'Attendance rate','Task completion'} else 'Lower is better'
        status='NO DATA' if actual is None or target is None else ('GREEN' if (actual>=target if direction=='Higher is better' else actual<=target) else 'RED')
        rows.append({'period':month,'department_id':'Company','metric':name,'target_value':target,'actual_value':actual,'direction':direction,'status':status,'variance':(actual-target) if actual is not None and target is not None else None,'sample_size':None})
    targets=pd.DataFrame(rows)
if targets.empty:
    st.info("No approved KPI target rows are available for the selected month and scope.")
else:
    target_table=targets.drop(columns=['period']).style.format({'target_value':'{:,.2f}','actual_value':'{:,.2f}','variance':'{:+,.2f}'}).map(status_color,subset=['status'])
    st.dataframe(target_table,use_container_width=True,hide_index=True)
    green=int((targets.status=='GREEN').sum()); red=int((targets.status=='RED').sum())
    insight(f"{green} KPI target groups are on target and {red} are off target; sample thresholds are applied to task groups.")
