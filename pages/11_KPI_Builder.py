import re
import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, insight, query_df, require_user

st.title("KPI builder and drill-down")
st.caption("Choose an official metric and a supported dimension. Role scope and minimum sample sizes are applied before results are returned.")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user=require_user()
catalog=query_df("SELECT metric_id,metric_name,view_name,unit,minimum_group_size,grain,caveat FROM metrics.metric_catalog ORDER BY metric_id")
if catalog.empty:
    st.error("Metric catalog is unavailable.")
    st.stop()
if user["role"]=="MANAGER":
    catalog=catalog[catalog.metric_id.isin(["M22","M23","M24","M25"])]
elif user["role"]=="HR":
    catalog=catalog[catalog.metric_id.isin([f"M{i:02d}" for i in range(1,16)]+["M22","M23","M24","M25","M27"])]
elif user["role"] not in {"ADMIN","HR"}:
    catalog=catalog[~catalog.metric_id.isin(["M07","M08","M09","M10","M11","M12","M15"])]

selected_id=st.selectbox("Official metric",catalog.metric_id.tolist(),format_func=lambda x:f"{x} · {catalog.loc[catalog.metric_id==x,'metric_name'].iloc[0]}")
metric=catalog.loc[catalog.metric_id==selected_id].iloc[0]
min_group=int(metric.minimum_group_size) if pd.notna(metric.minimum_group_size) else 0
task_metric=selected_id in {"M22","M23","M24","M25"}
if task_metric: min_group=max(5,min_group)

if user["role"]=="EXECUTIVE":
    dimensions=["Company"]
elif user["role"]=="MANAGER":
    dimensions=["Team"]
elif user["role"]=="HR" and task_metric:
    dimensions=["Department","Team"]
elif user["role"]=="HR":
    dimensions=["Department"]
elif task_metric:
    dimensions=["Company","Department","Team"]
elif selected_id in {"M01","M02","M03","M04","M05","M06","M07","M08","M09","M10","M11","M12","M13","M14","M15","M27","M28"}:
    dimensions=["Company","Department"]
elif selected_id=="M26":
    dimensions=["AI source"]
else:
    dimensions=["Company"]
dimension=st.selectbox("Drill-down dimension",dimensions)

dept_values=query_df("SELECT DISTINCT department_id FROM clean.dim_department ORDER BY 1").department_id.astype(str).tolist()
team_frame=query_df("SELECT team_id,team_name,department_id FROM clean.dim_team ORDER BY team_id")
if user["role"]=="HR":
    department=str(user["department_id"])
    st.caption(f"HR scope is fixed to {department}.")
elif dimension in {"Department","Team"} and user["role"]=="ADMIN":
    department=st.selectbox("Department scope",dept_values)
else:
    department=str(user.get("department_id") or "ALL")

if dimension=="Team":
    choices=team_frame
    if department!="ALL": choices=choices[choices.department_id.astype(str)==department]
    if user["role"]=="MANAGER": choices=choices[choices.team_id.astype(str)==str(user["team_id"])]
    if choices.empty:
        st.info("No team exists in this scope.")
        st.stop()
    team_id=st.selectbox("Team",choices.team_id.tolist(),format_func=lambda x:f"{x} · {choices.loc[choices.team_id==x,'team_name'].iloc[0]}")
else:
    team_id=None

view_name=str(metric.view_name)
if not re.fullmatch(r"[a-z0-9_]+",view_name):
    st.error("Catalog view name failed the safe identifier check.")
    st.stop()
period_options=[]
if task_metric:
    sprint_frame=query_df("SELECT sprint_id,sprint_name,start_date FROM clean.dim_sprint ORDER BY start_date")
    selected_sprint=st.selectbox("Sprint",sprint_frame.sprint_id.tolist(),index=len(sprint_frame)-1,format_func=lambda x:f"{x} · {sprint_frame.loc[sprint_frame.sprint_id==x,'sprint_name'].iloc[0]}")
else:
    if selected_id=="M26":
        p=query_df("SELECT DISTINCT CAST(date_trunc('month',period) AS DATE) AS period FROM clean.fact_anomaly ORDER BY 1")
    elif selected_id=="M27":
        p=query_df("SELECT DISTINCT period FROM metrics.m27_high_risk_share ORDER BY 1")
    elif selected_id=="M28":
        p=query_df("SELECT DISTINCT period FROM metrics.m28_forecast_error ORDER BY 1")
    elif selected_id in {"M20","M21"}:
        p=query_df(f"SELECT DISTINCT period FROM metrics.{view_name} ORDER BY 1")
    else:
        p=query_df(f"SELECT DISTINCT period FROM metrics.{view_name} ORDER BY 1")
    period_options=pd.to_datetime(p.period).dt.date.tolist() if not p.empty else []
    if not period_options:
        st.info("No periods are available for the selected metric.")
        st.stop()
    selected_period=st.selectbox("Period",period_options,index=len(period_options)-1)

if task_metric:
    base_condition=""
    params=[selected_sprint]
    if dimension=="Team":
        base_condition=" AND tm.team_id=?"; params.append(team_id)
        group="tm.team_id,tm.team_name,tm.department_id"
        label="tm.team_name"
    elif dimension=="Department":
        base_condition=" AND tm.department_id=?"; params.append(department)
        group="tm.department_id"
        label="tm.department_id"
    else:
        group=""
        label="'Company'"
    if selected_id=="M22":
        expr="100.0*COUNT(*) FILTER(WHERE t.status='Done')/NULLIF(COUNT(*) FILTER(WHERE t.status<>'Cancelled'),0)"
        sample="COUNT(*) FILTER(WHERE t.status<>'Cancelled')"
    elif selected_id=="M23":
        expr="100.0*COUNT(*) FILTER(WHERE t.completed_on_time='Y')/NULLIF(COUNT(*) FILTER(WHERE t.status='Done'),0)"
        sample="COUNT(*) FILTER(WHERE t.status='Done')"
    elif selected_id=="M24":
        expr="SUM(t.story_points) FILTER(WHERE t.status='Done')"
        sample="COUNT(*) FILTER(WHERE t.status<>'Cancelled')"
    else:
        expr="AVG(date_diff('day',t.started_date,t.completed_date)) FILTER(WHERE t.status='Done')"
        sample="COUNT(*) FILTER(WHERE t.status='Done')"
    group_sql=f"GROUP BY {group}" if group else ""
    query=f"""SELECT {label} AS group_name,{expr} AS value,{sample} AS sample_size
              FROM clean.fact_task t JOIN clean.dim_team tm USING(team_id)
              WHERE t.sprint_id=?{base_condition} {group_sql}
              HAVING {sample}>=? ORDER BY value DESC"""
    params.append(min_group)
    result=query_df(query,params)
    label_text={"M22":"Completion (%)","M23":"On-time delivery (%)","M24":"Completed story points","M25":"Average cycle time (days)"}[selected_id]
    note="These roll-ups use the dictionary formula over the clean task feed; teams smaller than five eligible tasks are suppressed. Canceled tasks are excluded from completion denominator."
elif selected_id=="M26":
    if dimension=="AI source":
        result=query_df("""SELECT source_dataset AS group_name,100.0*AVG(CASE WHEN flagged='Y' THEN 1.0 ELSE 0 END) AS value,
                           COUNT(*) AS sample_size FROM clean.fact_anomaly
                         WHERE CAST(date_trunc('month',period) AS DATE)=? GROUP BY 1 ORDER BY value DESC""",[selected_period])
    else:
        result=query_df("""SELECT 'Company' AS group_name,100.0*AVG(CASE WHEN flagged='Y' THEN 1.0 ELSE 0 END) AS value,
                           COUNT(*) AS sample_size FROM clean.fact_anomaly
                         WHERE CAST(date_trunc('month',period) AS DATE)=?""",[selected_period])
    label_text="Flagged records (%)"; note="Model flags are review leads, not proof. No employee identifiers are exposed."
elif selected_id=="M27" and dimension=="Company":
    result=query_df("""SELECT 'Company' AS group_name,100.0*COUNT(*) FILTER(WHERE risk_band='High')/NULLIF(COUNT(*),0) AS value,
                        COUNT(DISTINCT employee_id) AS sample_size FROM clean.fact_attrition_risk
                      WHERE as_of_date=? GROUP BY 1 HAVING COUNT(DISTINCT employee_id)>=?""",[selected_period,min_group])
    label_text="High-risk share (%)"; note="Predicted attrition risk only; the view is grouped and suppresses groups below the dictionary minimum."
elif selected_id=="M28" and dimension=="Company":
    result=query_df("""SELECT 'Company forecast error' AS group_name,NULL::DOUBLE AS value,
                        SUM(forecast_value) AS forecast_value,SUM(lower_80) AS lower_80,SUM(upper_80) AS upper_80,
                        'No actuals overlap the forecast horizon' AS measurement_status
                      FROM clean.fact_forecast WHERE metric='headcount_end' AND forecast_month=?""",[selected_period])
    label_text="MAPE (%)"; note="MAPE is not measurable because supplied actuals end before the first forecast period. Company forecast totals and 80% ranges remain available."
else:
    if selected_id=="M26":
        raise RuntimeError("Unreachable anomaly mapping")
    cols=query_df(f"SELECT * FROM metrics.{view_name} LIMIT 0").columns.tolist()
    if "department_id" in cols:
        if dimension=="Department":
            clause="department_id=?"; params=[selected_period,department]
        elif dimension=="Company":
            clause="department_id='ALL'"; params=[selected_period]
        else:
            clause="department_id=?"; params=[selected_period,department]
        result=query_df(f"SELECT department_id AS group_name,value FROM metrics.{view_name} WHERE period=? AND {clause}",params)
    else:
        result=query_df(f"SELECT 'Company' AS group_name,value FROM metrics.{view_name} WHERE period=?",[selected_period])
    if user["role"]=="HR" and dimension=="Department": result=result[result.group_name.astype(str)==str(department)]
    if selected_id=="M27": label_text="High-risk share (%)"; note="Predicted risk is not a fact; employee rows and names are hidden."
    elif selected_id=="M28": label_text="Forecast error (MAPE %)"; note="No overlapping actual forecast months exist in the supplied data; null results are expected."
    else: label_text=str(metric.unit); note=str(metric.caveat or "Metric definition is in the catalog.")

st.subheader(f"{metric.metric_name} · {dimension}")
if not result.empty:
    st.dataframe(result,use_container_width=True,hide_index=True)
    if "value" in result and result.value.notna().any():
        fig=px.bar(result.sort_values("value"),x="value",y="group_name",orientation="h",title=f"{metric.metric_name} by {dimension.lower()}",color_discrete_sequence=["#117C78"])
        fig.update_layout(template="plotly_white",xaxis_title=label_text,yaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
        best=result.loc[result.value.idxmax()]
        insight(f"{best.group_name} is highest at {float(best.value):,.2f}; this is a descriptive ranking, not a performance judgment.")
    st.caption(note)
    if min_group:
        st.caption(f"Minimum group rule: {min_group} {('eligible tasks' if task_metric else 'people/records')} per displayed group.")
else:
    st.info(f"No group meets the minimum sample size of {min_group} for this metric and scope.")

st.caption(f"Definition: {metric.metric_name}. {metric.caveat or ''} · Source: {metric.grain}.")
