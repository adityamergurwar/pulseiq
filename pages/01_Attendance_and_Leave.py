import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pulseiq.app_common import department_picker, ensure_database, insight, pct, query_df, require_user


st.title("Attendance and leave trends")
st.caption(
    "Attendance rate = present days plus half unpaid days, divided by scheduled working days. "
    "Weekends and public holidays are excluded from scheduled days."
)
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] == "MANAGER":
    st.info("Department-wide attendance and leave detail is not available to the manager persona.")
    st.stop()

department = department_picker(user)
available = query_df(
    "SELECT DISTINCT period FROM metrics.m13_attendance_rate WHERE department_id=? ORDER BY 1",
    [department],
)
if available.empty:
    st.info("No attendance metrics are available for this scope.")
    st.stop()

periods = pd.to_datetime(available.period).dt.date.tolist()
start = st.sidebar.selectbox(
    "Start month", periods, max(0, len(periods) - 12), key="attendance_start"
)
attendance = query_df(
    "SELECT period,value AS rate FROM metrics.m13_attendance_rate "
    "WHERE department_id=? AND period>=? ORDER BY 1",
    [department, start],
)
late = query_df(
    "SELECT period,100.0*value AS rate FROM metrics.m14_late_arrival_rate "
    "WHERE department_id=? AND period>=? ORDER BY 1",
    [department, start],
)
overtime = query_df(
    "SELECT period,value AS rate FROM metrics.m11_overtime_share "
    "WHERE department_id=? AND period>=? ORDER BY 1",
    [department, start],
)
leave_total = query_df(
    "SELECT period,leave_days FROM metrics.dashboard_leave_monthly "
    "WHERE department_id=? AND period>=? ORDER BY 1",
    [department, start],
)
leave_type = query_df(
    "SELECT period,leave_type,leave_days,people FROM metrics.dashboard_leave_type_monthly "
    "WHERE department_id=? AND period>=? ORDER BY period,leave_type",
    [department, start],
)
calendar = query_df(
    "SELECT period,public_holiday_count,long_weekend_holiday_count,holiday_dates "
    "FROM metrics.dashboard_calendar_monthly WHERE period>=? ORDER BY 1",
    [start],
)
holiday_leave = query_df(
    "SELECT period,holiday_group,requests FROM metrics.dashboard_leave_holiday "
    "WHERE department_id=? AND period>=? ORDER BY 1,2",
    [department, start],
)

c1, c2, c3 = st.columns(3)
if not attendance.empty:
    c1.metric("Latest attendance", pct(attendance.rate.iloc[-1], False))
if not late.empty:
    c2.metric("Latest late-arrival rate", pct(late.rate.iloc[-1]))
if not overtime.empty:
    c3.metric("Latest overtime share", pct(overtime.rate.iloc[-1]))

context = attendance.merge(leave_total, on="period", how="left")
context = context.merge(calendar, on="period", how="left")
context["leave_days"] = context.leave_days.fillna(0)
context["public_holiday_count"] = context.public_holiday_count.fillna(0).astype(int)
context["long_weekend_holiday_count"] = context.long_weekend_holiday_count.fillna(0).astype(int)
context["holiday_dates"] = context.holiday_dates.fillna("")

if not context.empty:
    fig = px.line(
        context,
        x="period",
        y="rate",
        markers=True,
        title=f"Attendance was {pct(context.rate.iloc[-1], False)} in {context.period.iloc[-1]:%b %Y}",
        color_discrete_sequence=["#117C78"],
    )
    marked = context[context.public_holiday_count > 0]
    if not marked.empty:
        custom = marked[["public_holiday_count", "long_weekend_holiday_count", "holiday_dates"]].to_numpy()
        fig.add_trace(go.Scatter(
            x=marked.period,
            y=marked.rate,
            mode="markers",
            name="Public holiday month",
            marker={"symbol": "diamond", "size": 11, "color": "#D17B0F"},
            customdata=custom,
            hovertemplate=(
                "%{x|%b %Y}<br>Attendance: %{y:.1%}<br>Public holidays: %{customdata[0]}"
                "<br>Friday/Monday holidays: %{customdata[1]}<br>Dates: %{customdata[2]}<extra></extra>"
            ),
        ))
    fig.update_layout(template="plotly_white", yaxis_tickformat=".0%", yaxis_title="Attendance rate", xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Orange diamonds mark months with public holidays. Friday/Monday holidays are highlighted as "
        "possible long-weekend anchors; calendar overlap is context, not proof of cause."
    )

    median_leave = float(context.leave_days.median())

    def possible_context(row):
        notes = []
        if row.public_holiday_count:
            notes.append(
                f"{row.public_holiday_count} public holiday(s), including "
                f"{row.long_weekend_holiday_count} Friday/Monday holiday(s)"
            )
        if row.leave_days > median_leave:
            notes.append(f"approved leave was above the selected-range median ({row.leave_days:,.0f} days)")
        elif row.leave_days:
            notes.append(f"approved leave totaled {row.leave_days:,.0f} days")
        if not notes:
            notes.append("no public holiday was recorded; absence mix and reporting coverage need review")
        return "Possible context: " + "; ".join(notes) + ". This is not a proven cause."

    unusual = context.nsmallest(min(3, len(context)), "rate").copy()
    unusual["attendance_pct"] = (100 * unusual.rate).round(2)
    unusual["possible_context"] = unusual.apply(possible_context, axis=1)
    st.subheader("Three unusual months")
    st.caption("Lowest attendance rates in the selected range, with calendar and leave context for follow-up.")
    st.dataframe(
        unusual[[
            "period", "attendance_pct", "leave_days", "public_holiday_count",
            "long_weekend_holiday_count", "possible_context",
        ]].rename(columns={
            "period": "Month",
            "attendance_pct": "Attendance (%)",
            "leave_days": "Approved leave days",
            "public_holiday_count": "Public holidays",
            "long_weekend_holiday_count": "Friday/Monday holidays",
            "possible_context": "Possible explanation",
        }),
        use_container_width=True,
        hide_index=True,
    )

    if department == "ALL":
        change = query_df(
            """WITH monthly AS (
                 SELECT department_id,period,value,
                        LAG(value) OVER (PARTITION BY department_id ORDER BY period) AS prior_rate
                 FROM metrics.m13_attendance_rate WHERE department_id<>'ALL'
               )
               SELECT department_id,period,100.0*(value-prior_rate) AS change_pp
               FROM monthly WHERE prior_rate IS NOT NULL AND period>=?
               ORDER BY change_pp LIMIT 1""",
            [start],
        )
        if not change.empty:
            row = change.iloc[0]
            st.caption(
                f"After a company-wide dip, check the department with the largest month-over-month decline first: "
                f"{row.department_id} moved {row.change_pp:+.2f} percentage points in {row.period:%b %Y}. "
                "A rate change helps prioritize follow-up; the underlying attendance records still need review."
            )

if not leave_total.empty:
    peak = leave_total.loc[leave_total.leave_days.idxmax()]
    fig = px.bar(
        leave_total,
        x="period",
        y="leave_days",
        title=f"Approved leave peaked at {peak.leave_days:,.0f} days in {peak.period:%b %Y}",
        color_discrete_sequence=["#117C78"],
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Approved leave days")
    st.plotly_chart(fig, use_container_width=True)
    insight(f"Approved leave reached {peak.leave_days:,.0f} days in {peak.period:%b %Y} for {department}.")

if not leave_type.empty:
    fig = px.bar(
        leave_type,
        x="period",
        y="leave_days",
        color="leave_type",
        barmode="stack",
        title="Approved leave days by leave type",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Approved leave days", legend_title="Leave type")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(leave_type, use_container_width=True, hide_index=True)
else:
    st.info("No leave-type group meets the minimum display size for this scope.")

left, right = st.columns(2)
if not late.empty:
    peak = late.loc[late.rate.idxmax()]
    fig = px.line(
        late, x="period", y="rate", markers=True,
        title=f"Late arrivals peaked at {peak.rate:.1f}% of present days",
        color_discrete_sequence=["#D17B0F"],
    )
    fig.update_layout(template="plotly_white", yaxis_title="Late arrivals / present days (%)", xaxis_title=None)
    left.plotly_chart(fig, use_container_width=True)
    insight(f"Late arrivals peaked at {peak.rate:.1f}% in {peak.period:%b %Y}.")
if not overtime.empty:
    peak = overtime.loc[overtime.rate.idxmax()]
    fig = px.line(
        overtime, x="period", y="rate", markers=True,
        title=f"Overtime share peaked at {peak.rate:.1f}% of payroll cost",
        color_discrete_sequence=["#117C78"],
    )
    fig.update_layout(template="plotly_white", yaxis_title="Overtime share (%)", xaxis_title=None)
    right.plotly_chart(fig, use_container_width=True)
    insight(f"Overtime share reached {peak.rate:.1f}% in {peak.period:%b %Y}.")

if not holiday_leave.empty:
    fig = px.bar(
        holiday_leave,
        x="period",
        y="requests",
        color="holiday_group",
        barmode="group",
        title="Approved leave requests that overlap public holidays",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Leave requests", legend_title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(holiday_leave, use_container_width=True, hide_index=True)
