import pandas as pd
import plotly.express as px
import streamlit as st

from pulseiq.app_common import department_picker, ensure_database, insight, require_user
from pulseiq.app_common import query_df


st.title("Attrition analytics")
st.caption(
    "Observed exits and predicted risk are shown in separate sections. Attrition is exits divided by "
    "starting headcount; prediction results are aggregated and do not identify people."
)
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()

user = require_user()
if user["role"] == "MANAGER":
    st.info("Attrition detail is limited to HR and executive roles in this demo.")
    st.stop()

department = department_picker(user)
view = "dashboard_attrition_company" if department == "ALL" else "dashboard_attrition"
actual = query_df(
    f"SELECT period,exits,voluntary_exits,exits-voluntary_exits AS other_exits,attrition_pct "
    f"FROM metrics.{view} WHERE department_id=? ORDER BY period",
    [department],
)
if actual.empty:
    st.info("No sufficiently large group is available for this scope.")
    st.stop()

periods = pd.to_datetime(actual.period).dt.date.tolist()
start = st.sidebar.selectbox("Start month", periods, max(0, len(periods) - 12), key="attrition_start")
actual = actual[pd.to_datetime(actual.period).dt.date >= start].copy()

st.subheader("Observed exits")
st.caption("Other exits = total exits minus voluntary exits, using the supplied monthly headcount facts.")
if not actual.empty:
    fig = px.bar(
        actual,
        x="period",
        y=["voluntary_exits", "other_exits"],
        barmode="stack",
        title="Voluntary and other exits by month",
        color_discrete_sequence=["#117C78", "#D17B0F"],
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="People", legend_title=None)
    st.plotly_chart(fig, use_container_width=True)
    peak_exits = actual.loc[actual.exits.idxmax()]
    insight(
        f"Exits peaked at {peak_exits.exits:,.0f} in {peak_exits.period:%b %Y}: "
        f"{peak_exits.voluntary_exits:,.0f} voluntary and {peak_exits.other_exits:,.0f} other."
    )

    fig = px.line(
        actual,
        x="period",
        y="attrition_pct",
        markers=True,
        title="Monthly attrition rate",
        color_discrete_sequence=["#117C78"],
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Exits / starting headcount (%)")
    st.plotly_chart(fig, use_container_width=True)
    peak_rate = actual.loc[actual.attrition_pct.idxmax()]
    insight(
        f"Monthly attrition peaked at {peak_rate.attrition_pct:.2f}% in {peak_rate.period:%b %Y}; "
        "the denominator is starting headcount."
    )

left, right = st.columns(2)
tenure = query_df(
    "SELECT tenure_band,exits FROM metrics.dashboard_exit_tenure "
    "WHERE department_id=? ORDER BY exits DESC",
    [department],
)
reasons = query_df(
    "SELECT reason,exits FROM metrics.dashboard_exit_reasons "
    "WHERE department_id=? ORDER BY exits DESC",
    [department],
)
if not tenure.empty:
    top_tenure = tenure.iloc[0]
    fig = px.bar(
        tenure,
        x="tenure_band",
        y="exits",
        title="Tenure at exit (groups of five or more)",
        color_discrete_sequence=["#117C78"],
    )
    fig.update_layout(template="plotly_white", xaxis_title="Tenure band", yaxis_title="Exits")
    left.plotly_chart(fig, use_container_width=True)
    insight(f"The largest tenure band is {top_tenure.tenure_band}, with {top_tenure.exits:,.0f} exits.")
if not reasons.empty:
    fig = px.bar(
        reasons,
        x="reason",
        y="exits",
        title="Recorded exit categories (groups of five or more)",
        color_discrete_sequence=["#117C78"],
    )
    fig.update_layout(template="plotly_white", xaxis_title=None, yaxis_title="Exits")
    right.plotly_chart(fig, use_container_width=True)
    top_reason = reasons.iloc[0]
    insight(
        f"The largest recorded exit category is {top_reason.reason}, with {top_reason.exits:,.0f} exits; "
        "source reason labels are not independently verified."
    )
else:
    st.info("No tenure or exit-reason group meets the minimum display size of five.")

st.subheader("Predicted, not certain")
st.warning(
    "This is a baseline model signal for follow-up, not an observed exit or a decision about a person. "
    "Only risk bands with at least 10 people are displayed."
)
if department == "ALL":
    risk = query_df(
        "SELECT risk_band,people,average_risk_score FROM metrics.dashboard_predicted_risk_company ORDER BY risk_band"
    )
else:
    risk = query_df(
        "SELECT risk_band,people,average_risk_score FROM metrics.dashboard_predicted_risk "
        "WHERE department_id=? ORDER BY risk_band",
        [department],
    )
if not risk.empty:
    fig = px.bar(
        risk,
        x="risk_band",
        y="people",
        title=f"Latest grouped risk snapshot: {int(risk.people.sum()):,} people",
        color_discrete_sequence=["#D17B0F"],
    )
    fig.update_layout(template="plotly_white", xaxis_title="Predicted risk band", yaxis_title="People")
    st.plotly_chart(fig, use_container_width=True)
    high_risk = risk.loc[risk.risk_band == "High"]
    high_count = int(high_risk.people.sum()) if not high_risk.empty else 0
    insight(f"The grouped snapshot contains {high_count:,} people in the High predicted-risk band.")
else:
    st.info("No predicted-risk group meets the minimum display size of 10.")
