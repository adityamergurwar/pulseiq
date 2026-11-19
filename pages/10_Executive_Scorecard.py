import html

import pandas as pd
import streamlit as st

from pulseiq.app_common import company_metric_for_period, ensure_database, query_df, require_user


st.set_page_config(page_title="PulseIQ | Company scorecard", page_icon="◉", layout="wide")
st.markdown(
    """<style>
    .scorecard-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin-top:16px; }
    .scorecard-card { border:1px solid #dce5ed; border-radius:18px; padding:17px 18px; background:linear-gradient(145deg,#fff 0%,#f9fbfc 100%);
      color:#10233f; min-height:215px; box-shadow:0 12px 32px rgba(16,35,63,.07); position:relative; overflow:hidden; transition:transform .18s ease,box-shadow .18s ease; }
    .scorecard-card:before { content:""; position:absolute; left:0; top:0; right:0; height:4px; background:linear-gradient(90deg,#0f766e,#2dd4bf); }
    .scorecard-card:hover { transform:translateY(-2px); box-shadow:0 16px 38px rgba(16,35,63,.1); }
    .scorecard-card h3 { margin:10px 0 5px; font-size:18px; color:#10233f; letter-spacing:-.02em; }
    .scorecard-card .metric-id { color:#63778b; font-size:11px; font-weight:800; letter-spacing:.09em; }
    .scorecard-card .value { font-size:27px; line-height:1.2; font-weight:800; color:#0f766e; margin:6px 0 11px; letter-spacing:-.035em; }
    .scorecard-card p { margin:4px 0; font-size:13px; color:#334a60; }
    .scorecard-card .why { min-height:40px; color:#52667a; }
    .scorecard-card a { display:inline-block; margin-top:9px; padding:6px 9px; border-radius:8px; background:#e7f5f2;
      border:1px solid #c7e7e1; font-size:12px; font-weight:750; color:#0b625c; text-decoration:none; }
    .status { display:inline-block; border-radius:99px; padding:4px 9px; font-size:10px; font-weight:800; letter-spacing:.035em; }
    .status.good { background:#dcfce7; color:#166534; }
    .status.bad { background:#fee2e2; color:#991b1b; }
    .status.neutral { background:#e2e8f0; color:#475569; }
    @media (max-width:900px) { .scorecard-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media print {
      @page { size:A4 landscape; margin:8mm; }
      header, footer, [data-testid='stSidebar'], [data-testid='stToolbar'], [data-testid='stDecoration'] { display:none!important; }
      .block-container { max-width:none!important; padding:0!important; }
      .scorecard-grid { grid-template-columns:repeat(4,minmax(0,1fr))!important; gap:2.5mm!important; }
      .scorecard-card { min-height:37mm!important; padding:2.5mm!important; border-radius:2mm!important; break-inside:avoid; }
      .scorecard-card h3 { font-size:10pt!important; }
      .scorecard-card .value { font-size:15pt!important; margin:1mm 0 2mm!important; }
      .scorecard-card p, .scorecard-card a { font-size:7.5pt!important; }
      .scorecard-card .why { min-height:8mm!important; }
      .status { font-size:6.5pt!important; }
      [data-testid='stAppViewContainer'] { overflow:visible!important; }
      * { -webkit-print-color-adjust:exact!important; print-color-adjust:exact!important; }
    }
    </style>""",
    unsafe_allow_html=True,
)

st.title("Executive company health scorecard")
st.caption("Eight governed KPIs · selected month · targets only where an approved target exists")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] not in {"ADMIN", "EXECUTIVE"}:
    st.info("The company scorecard is restricted to Admin and Executive personas; HR and Manager use their scoped pages.")
    st.stop()

dates = query_df("SELECT DISTINCT period FROM metrics.m01_headcount WHERE department_id='ALL' ORDER BY 1")
periods = pd.to_datetime(dates.period).dt.date.tolist()
if not periods:
    st.info("No company scorecard month is available.")
    st.stop()
selected = st.sidebar.selectbox("Scorecard month", periods, index=len(periods) - 1)
period = pd.Timestamp(selected).replace(day=1).date()
month_end = (pd.Timestamp(period) + pd.offsets.MonthEnd(0)).date()

metric_specs = [
    ("M01", "Headcount", "metrics.m01_headcount", "count", "/", "Workforce scale helps leaders size capacity and hiring plans.", "Workforce and headcount"),
    ("M04", "Monthly attrition", "metrics.m04_attrition_monthly", "percent", "/Attrition", "Shows workforce stability and likely replacement pressure.", "Attrition"),
    ("M09", "Employer payroll cost", "metrics.m09_payroll_cost", "money", "/Payroll_and_Cost", "Tracks the largest recurring people-cost base.", "Payroll and cost"),
    ("M13", "Attendance rate", "metrics.m13_attendance_rate", "ratio", "/Attendance_and_Leave", "Shows workforce availability against scheduled working days.", "Attendance and leave"),
    ("M16", "Revenue", "metrics.m16_revenue", "money", "/PnL_and_Expenses", "Tracks the value of delivered commercial activity.", "P&L and expenses"),
    ("M18", "Operating margin", "metrics.m18_operating_margin", "percent", "/PnL_and_Expenses", "Shows how much revenue remains after ledger expenses.", "P&L and expenses"),
    ("M20", "Days sales outstanding", "metrics.m20_dso", "days", "/Receivables_and_Cash", "Shows how quickly billed sales convert into cash.", "Receivables and cash"),
    ("M22", "Task completion", "metrics.dashboard_task_completion_monthly", "percent", "/Team_Productivity", "Tracks delivery throughput after cancelled work is excluded.", "Team productivity"),
]

target_rows = query_df(
    """SELECT metric, AVG(target_value) AS target_value, MIN(direction) AS direction
       FROM metrics.dashboard_kpi_targets WHERE period=? GROUP BY 1""",
    [period],
)
targets = {
    row.metric: {"value": float(row.target_value), "direction": str(row.direction)}
    for _, row in target_rows.iterrows()
    if pd.notna(row.target_value)
}

def metric_value(view, selected_period):
    if view == "metrics.m20_dso":
        selected_period = (pd.Timestamp(selected_period) + pd.offsets.MonthEnd(0)).date()
    result = company_metric_for_period(view, selected_period)
    return None if result.empty or pd.isna(result.iloc[0, 0]) else float(result.iloc[0, 0])

def fmt_value(value, unit):
    if value is None:
        return "Not available"
    if unit == "money":
        return f"INR {value:,.0f}"
    if unit == "count":
        return f"{value:,.0f}"
    if unit == "ratio":
        return f"{value:.1%}"
    if unit == "days":
        return f"{value:.1f} days"
    return f"{value:.1f}%"

def fmt_trend(current, previous, unit):
    if current is None or previous is None:
        return "No prior month"
    delta = current - previous
    if unit == "money":
        return f"{delta:+,.0f} vs prior month"
    if unit == "count":
        return f"{delta:+,.0f} vs prior month"
    if unit == "days":
        return f"{delta:+.1f} days vs prior month"
    if unit == "ratio":
        return f"{delta * 100:+.1f} pp vs prior month"
    return f"{delta:+.1f} pp vs prior month"

previous_period = (pd.Timestamp(period) - pd.offsets.MonthBegin(1)).date()
cards = []
for metric_id, label, view, unit, path, rationale, detail_label in metric_specs:
    value = metric_value(view, period)
    previous = metric_value(view, previous_period)
    target_name = {
        "M04": "Monthly attrition",
        "M13": "Attendance rate",
        "M22": "Task completion",
    }.get(metric_id)
    target = targets.get(target_name) if target_name else None
    if target is None:
        target_text = "Not set"
        status_text = "NO APPROVED TARGET"
        status_class = "neutral"
    else:
        target_value = target["value"]
        comparison_value = value * 100 if unit == "ratio" and value is not None else value
        if comparison_value is None:
            status_text, status_class = "NO DATA", "neutral"
        else:
            is_higher_better = target["direction"] == "Higher is better"
            is_on_target = comparison_value >= target_value if is_higher_better else comparison_value <= target_value
            status_text = "ON TARGET" if is_on_target else "OFF TARGET"
            status_class = "good" if is_on_target else "bad"
        target_text = f"{target_value:.1f}%"
    cards.append(
        {
            "id": metric_id,
            "name": label,
            "value": fmt_value(value, unit),
            "target": target_text,
            "trend": fmt_trend(value, previous, unit),
            "status": status_text,
            "status_class": status_class,
            "rationale": rationale,
            "path": path,
            "detail": detail_label,
        }
    )

st.caption(f"Selected month: {pd.Timestamp(period):%B %Y} · data cut-off: {pd.Timestamp(month_end):%d %b %Y}")
card_html = []
for card in cards:
    card_html.append(
        "<section class='scorecard-card'>"
        f"<div><span class='metric-id'>{html.escape(card['id'])}</span> "
        f"<span class='status {html.escape(card['status_class'])}'>{html.escape(card['status'])}</span></div>"
        f"<h3>{html.escape(card['name'])}</h3>"
        f"<div class='value'>{html.escape(card['value'])}</div>"
        f"<p><b>Target:</b> {html.escape(card['target'])}</p>"
        f"<p><b>Trend:</b> {html.escape(card['trend'])}</p>"
        f"<p class='why'>{html.escape(card['rationale'])}</p>"
        f"<a href='{html.escape(card['path'], quote=True)}' target='_self'>Open {html.escape(card['detail'])}</a>"
        "</section>"
    )
st.markdown("<div class='scorecard-grid'>" + "".join(card_html) + "</div>", unsafe_allow_html=True)
st.caption("All values come from governed metric views. Target statuses follow the supplied KPI targets; no target is invented for the other metrics.")
st.caption("For a five-KPI founder view, retain revenue, operating margin, days sales outstanding, employer payroll cost and attrition. Attendance, headcount and task completion remain available on linked pages for operating context.")
