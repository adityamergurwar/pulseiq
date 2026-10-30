import pandas as pd
import streamlit as st

from pulseiq.app_common import DB_PATH, company_metric_for_period, ensure_database, insight, money, query_df, require_user

st.set_page_config(page_title="PulseIQ | Company scorecard", page_icon="◉", layout="wide")
st.markdown("""<style>
.block-container{max-width:1180px;padding-top:1rem;padding-bottom:.5rem}
@media print{header,footer,[data-testid='stSidebar'],[data-testid='stToolbar']{display:none!important}.block-container{padding:0!important}}
</style>""",unsafe_allow_html=True)
st.title("Executive company health scorecard")
st.caption("Eight dictionary metrics · selected month · target status only where an approved target exists")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user=require_user()
if user["role"] not in {"ADMIN","EXECUTIVE"}:
    st.info("The company scorecard is restricted to Admin and Executive roles; HR and Manager use their scoped pages.")
    st.stop()
dates=query_df("SELECT DISTINCT period FROM metrics.m01_headcount WHERE department_id='ALL' ORDER BY 1")
periods=pd.to_datetime(dates.period).dt.date.tolist()
selected=st.sidebar.selectbox("Scorecard month",periods,index=len(periods)-1)
period=pd.Timestamp(selected).replace(day=1).date()
month_end=(pd.Timestamp(period)+pd.offsets.MonthEnd(0)).date()

metrics=[
    ("M01","Headcount","metrics.m01_headcount","count","month"),
    ("M04","Monthly attrition","metrics.m04_attrition_monthly","percent","month"),
    ("M13","Attendance rate","metrics.m13_attendance_rate","ratio","month"),
    ("M11","Overtime share","metrics.m11_overtime_share","percent","month"),
    ("M09","Employer payroll cost","metrics.m09_payroll_cost","money","month"),
    ("M16","Revenue","metrics.m16_revenue","money","month"),
    ("M18","Operating margin","metrics.m18_operating_margin","percent","month"),
]
values=[]
for mid,label,view,unit,grain in metrics:
    df=company_metric_for_period(view,period)
    prev_period=(pd.Timestamp(period)-pd.offsets.MonthBegin(1)).date()
    prev=company_metric_for_period(view,prev_period)
    value=None if df.empty else float(df.iloc[0,0])
    previous=None if prev.empty else float(prev.iloc[0,0])
    values.append({"id":mid,"name":label,"value":value,"previous":previous,"unit":unit})

task=company_metric_for_period("metrics.dashboard_task_completion_monthly",period)
prev_period=(pd.Timestamp(period)-pd.offsets.MonthBegin(1)).date()
prev_task=company_metric_for_period("metrics.dashboard_task_completion_monthly",prev_period)
values.append({"id":"M22","name":"Task completion","value":None if task.empty else float(task.iloc[0,0]),"previous":None if prev_task.empty else float(prev_task.iloc[0,0]),"unit":"percent"})

target_rows=query_df("SELECT metric,AVG(target_value) AS target_value FROM metrics.dashboard_kpi_targets WHERE period=? GROUP BY 1",[period])
targets={r.metric:float(r.target_value) for _,r in target_rows.iterrows() if pd.notna(r.target_value)}
target_name={"M04":"Monthly attrition","M11":"Overtime share","M13":"Attendance rate","M22":"Task completion"}
target_for={"M04":"Monthly attrition","M11":"Overtime share","M13":"Attendance rate","M22":"Task completion"}
cards=[]
for item in values:
    value=item["value"]; previous=item["previous"]; name=item["name"]
    if value is None:
        shown="Not available"; trend="No row"
    elif item["unit"]=="money":
        shown=money(value); trend=f"{(value-previous):+,.0f} vs prior month" if previous is not None else "First month"
    elif item["unit"]=="count":
        shown=f"{value:,.0f}"; trend=f"{value-previous:+,.0f} vs prior month" if previous is not None else "First month"
    elif item["unit"]=="ratio":
        shown=f"{value:.1%}"; trend=f"{(value-previous)*100:+.1f} pp vs prior month" if previous is not None else "First month"
    else:
        shown=f"{value:.1f}%"; trend=f"{value-previous:+.1f} pp vs prior month" if previous is not None else "First month"
    target=targets.get(target_for.get(item["id"],""))
    if target is None:
        status="NO APPROVED TARGET"; target_text="Not set"
    else:
        if item["unit"]=="ratio": value_for_status=value*100 if value is not None else None
        else: value_for_status=value
        target_text=f"{target:.1f}%"
        low_is_good=item["id"] in {"M04","M11"}
        status="NO DATA" if value_for_status is None else ("ON TARGET" if ((value_for_status<=target) if low_is_good else (value_for_status>=target)) else "OFF TARGET")
    cards.append({"Metric":name,"Value":shown,"Target":target_text,"Trend":trend,"Status":status,"Source":item["id"]})

st.caption(f"Selected month: {pd.Timestamp(period):%B %Y} · data cut-off: {pd.Timestamp(month_end):%d %b %Y}")
grid=st.columns(4)
for i,row in enumerate(cards):
    with grid[i%4]:
        st.metric(row["Metric"],row["Value"],row["Trend"])
        st.caption(f"Target: {row['Target']} · {row['Status']} · {row['Source']}")
        if i==3: grid=st.columns(4)

st.dataframe(pd.DataFrame(cards),hide_index=True,use_container_width=True)
st.caption("Targets are available for attendance, overtime share, monthly attrition and task completion. The remaining four metrics have no approved target in the supplied KPI target feed. Values trace to governed metric views; task completion uses its documented formula aggregated across the selected month's sprints.")
st.info("Use the browser print command to print this compact scorecard. Select a month in the sidebar before printing.")
