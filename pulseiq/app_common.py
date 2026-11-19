"""Shared Streamlit access rules, data access and UI helpers."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import binascii
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("PULSEIQ_DB_PATH", ROOT / "pulseiq.duckdb"))
DEMO_USERS = ROOT / "05_Starter" / "demo_users.csv"

_SCORECARD_VIEWS = {
    "metrics.m01_headcount",
    "metrics.m04_attrition_monthly",
    "metrics.m13_attendance_rate",
    "metrics.m11_overtime_share",
    "metrics.m09_payroll_cost",
    "metrics.m16_revenue",
    "metrics.m18_operating_margin",
    "metrics.m20_dso",
    "metrics.dashboard_task_completion_monthly",
}
_SCORECARD_GLOBAL_VIEWS = {
    "metrics.m16_revenue",
    "metrics.m18_operating_margin",
    "metrics.m20_dso",
}


def _install_plotly_theme() -> None:
    """Apply one presentation system to every Plotly chart in the app."""
    theme = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0A0F17",
            colorway=["#2DD4BF", "#60A5FA", "#F59E0B", "#A78BFA", "#FB7185", "#22D3EE"],
            font={"family": "Inter, Segoe UI, Arial, sans-serif", "size": 13, "color": "#D7E2EC"},
            title={"font": {"family": "Inter, Segoe UI, Arial, sans-serif", "size": 19, "color": "#F7FAFC"}, "x": 0.01, "xanchor": "left"},
            margin={"l": 28, "r": 22, "t": 70, "b": 42},
            hoverlabel={"bgcolor": "#111A27", "bordercolor": "#334155", "font": {"color": "#FFFFFF", "size": 12}},
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "font": {"size": 11}},
            xaxis={"showgrid": False, "linecolor": "#2A3748", "tickcolor": "#475569", "zerolinecolor": "#475569", "title_font": {"size": 12, "color": "#9FB0C2"}},
            yaxis={"showgrid": True, "gridcolor": "#202B3A", "gridwidth": 1, "zerolinecolor": "#475569", "title_font": {"size": 12, "color": "#9FB0C2"}},
            bargap=0.28, hovermode="closest",
        )
    )
    pio.templates["pulseiq"] = theme
    pio.templates["plotly_white"] = theme
    pio.templates["plotly_dark"] = theme
    pio.templates.default = "pulseiq"


def apply_design_system() -> None:
    """Install the PulseIQ executive dashboard styling for the current page."""
    _install_plotly_theme()
    st.markdown(
        """<style>
        :root { --pulse-navy:#F7FAFC; --pulse-navy-2:#D8E2EC; --pulse-teal:#2DD4BF;
          --pulse-teal-soft:#102C2B; --pulse-amber:#F59E0B; --pulse-canvas:#06090F;
          --pulse-card:#0D131D; --pulse-card-2:#111A27; --pulse-border:#263244; --pulse-muted:#98A8BA; }
        html, body, [class*="css"] { font-family:Inter,"Segoe UI",Arial,sans-serif; color-scheme:dark; }
        .stApp { background:radial-gradient(circle at 82% -12%,rgba(45,212,191,.105),transparent 32rem),
          radial-gradient(circle at 15% 105%,rgba(37,99,235,.08),transparent 28rem),
          linear-gradient(180deg,#080C13 0%,var(--pulse-canvas) 100%); color:#E6EDF5; }
        [data-testid="stAppViewContainer"] > .main { background:transparent; }
        .block-container { max-width:1500px; padding:1.65rem 2.25rem 4rem; }
        h1 { color:var(--pulse-navy)!important; font-size:clamp(2.15rem,3vw,3.15rem)!important;
          line-height:1.04!important; letter-spacing:-.045em!important; font-weight:800!important; margin-bottom:.35rem!important; }
        h2 { color:var(--pulse-navy)!important; font-size:1.55rem!important; letter-spacing:-.025em!important;
          margin-top:2.2rem!important; padding-left:.8rem; border-left:4px solid var(--pulse-teal); }
        h3 { color:var(--pulse-navy)!important; letter-spacing:-.015em; }
        p, li { line-height:1.62; }
        [data-testid="stCaptionContainer"] { color:var(--pulse-muted)!important; font-size:.9rem!important; }
        [data-testid="stSidebar"] { background:linear-gradient(180deg,#04070B 0%,#080D15 55%,#0B171C 100%);
          border-right:1px solid rgba(255,255,255,.08); }
        [data-testid="stSidebar"] > div:first-child { padding-top:.45rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] h3 { color:#E8F0F7!important; }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#D7E3EE!important; font-weight:650!important; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] input { background:rgba(255,255,255,.095)!important; border:1px solid rgba(255,255,255,.15)!important;
          color:#FFFFFF!important; border-radius:11px!important; min-height:44px; }
        [data-testid="stSidebar"] [data-baseweb="select"] span { color:#FFFFFF!important; }
        [data-testid="stSidebarNav"] { padding-top:.35rem; }
        [data-testid="stSidebarNav"] a { border-radius:10px; margin:.12rem .55rem; padding:.58rem .72rem; color:#DBE7F1; }
        [data-testid="stSidebarNav"] a:hover { background:rgba(255,255,255,.09); }
        [data-testid="stSidebarNav"] a[aria-current="page"] { background:linear-gradient(90deg,rgba(20,184,166,.26),rgba(255,255,255,.08));
          box-shadow:inset 3px 0 0 #2DD4BF; color:#FFFFFF; font-weight:700; }
        .pulse-brand { margin:.1rem .55rem 1.15rem; padding:1rem 1rem .9rem; border:1px solid rgba(255,255,255,.12);
          background:linear-gradient(135deg,rgba(255,255,255,.11),rgba(45,212,191,.08)); border-radius:15px; }
        .pulse-brand-row { display:flex; align-items:center; gap:.72rem; }
        .pulse-logo { width:36px; height:36px; display:grid; place-items:center; border-radius:11px;
          background:linear-gradient(135deg,#2DD4BF,#0F766E); color:white; font-weight:900; font-size:1rem; box-shadow:0 8px 24px rgba(45,212,191,.24); }
        .pulse-brand-name { color:white; font-weight:800; font-size:1.05rem; letter-spacing:-.02em; }
        .pulse-brand-sub { color:#AFC4D5; font-size:.72rem; margin-top:.08rem; letter-spacing:.06em; text-transform:uppercase; }
        .pulse-context { display:flex; flex-wrap:wrap; gap:.55rem; align-items:center; margin:.7rem 0 1.35rem;
          padding:.72rem .88rem; background:rgba(13,19,29,.88); border:1px solid var(--pulse-border); border-radius:13px;
          box-shadow:0 12px 34px rgba(0,0,0,.28); backdrop-filter:blur(10px); }
        .pulse-context-label { color:var(--pulse-muted); font-size:.76rem; font-weight:700; letter-spacing:.055em; text-transform:uppercase; }
        .pulse-chip { display:inline-flex; align-items:center; gap:.35rem; background:var(--pulse-teal-soft); color:#69E5D7;
          border:1px solid #1F5753; border-radius:999px; padding:.3rem .62rem; font-size:.76rem; font-weight:750; }
        .pulse-chip.secondary { background:#151E2A; color:#B5C2D0; border-color:#2A3748; }
        [data-testid="stMetric"] { background:linear-gradient(145deg,#111925 0%,#0B111A 100%); border:1px solid var(--pulse-border);
          border-radius:17px; padding:1rem 1.08rem; min-height:128px; box-shadow:0 14px 34px rgba(0,0,0,.3); position:relative; overflow:hidden; }
        [data-testid="stMetric"]:before { content:""; position:absolute; left:0; top:0; right:0; height:4px;
          background:linear-gradient(90deg,var(--pulse-teal),#22C3B6); }
        [data-testid="stMetricLabel"] p { color:#98A8BA!important; font-size:.8rem!important; font-weight:700!important; letter-spacing:.035em; text-transform:uppercase; }
        [data-testid="stMetricValue"] { color:var(--pulse-navy)!important; font-weight:790!important; letter-spacing:-.035em; }
        [data-testid="stMetricDelta"] { font-weight:650; }
        [data-testid="stPlotlyChart"] { background:linear-gradient(145deg,#0E1520,#090E16); border:1px solid var(--pulse-border); border-radius:18px;
          padding:.55rem .65rem .2rem; box-shadow:0 16px 38px rgba(0,0,0,.32); overflow:hidden; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { background:var(--pulse-card); border:1px solid var(--pulse-border);
          border-radius:15px; overflow:hidden; box-shadow:0 14px 34px rgba(0,0,0,.27); }
        [data-testid="stAlert"] { border-radius:14px; border-width:1px; box-shadow:0 10px 28px rgba(0,0,0,.22); }
        div[data-testid="stForm"] { background:rgba(255,255,255,.035); border:1px solid rgba(255,255,255,.1); border-radius:14px; padding:.75rem; }
        div[data-baseweb="select"] > div, input, textarea { border-radius:11px!important; border-color:#344155!important; background:#0E1520!important; color:#F7FAFC!important; }
        .stButton > button, [data-testid="stFormSubmitButton"] button { border-radius:11px; font-weight:750; min-height:42px;
          background:#152235; color:white; border:1px solid #33445B; }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { background:#145E58; border-color:#2DD4BF; color:white; }
        .pulse-insight { margin:.65rem 0 1.1rem; padding:.85rem 1rem; border-radius:13px; background:linear-gradient(90deg,#0E2928,#101B23);
          border:1px solid #22514E; color:#CDE8E5; display:flex; gap:.72rem; align-items:flex-start; box-shadow:0 12px 28px rgba(0,0,0,.24); }
        .pulse-insight-mark { flex:0 0 auto; width:27px; height:27px; display:grid; place-items:center; border-radius:8px;
          background:var(--pulse-teal); color:white; font-size:.76rem; font-weight:900; }
        .pulse-insight strong { color:#67E8D8; }
        hr { border-color:var(--pulse-border)!important; }
        @media (max-width:900px) { .block-container { padding:1.25rem 1rem 3rem; } h1 { font-size:2.05rem!important; }
          [data-testid="stMetric"] { min-height:110px; } .pulse-context { align-items:flex-start; } }
        @media print { [data-testid="stSidebar"], [data-testid="stToolbar"], header { display:none!important; }
          .stApp { background:white!important; } [data-testid="stMetric"], [data-testid="stPlotlyChart"] { box-shadow:none!important; } }
        </style>""",
        unsafe_allow_html=True,
    )


def _render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """<div class="pulse-brand"><div class="pulse-brand-row"><div class="pulse-logo">PI</div>
        <div><div class="pulse-brand-name">PulseIQ</div><div class="pulse-brand-sub">Decision intelligence</div></div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def _render_context(user: dict[str, Any]) -> None:
    role = html.escape(str(user.get("role", "EXECUTIVE")).title())
    scope = html.escape(str(user.get("team_id") or user.get("department_id") or "Company"))
    st.markdown(
        f"""<div class="pulse-context"><span class="pulse-context-label">Current view</span>
        <span class="pulse-chip">{role} · {scope}</span>
        <span class="pulse-chip secondary">Data cut-off · 30 Sep 2026</span>
        <span class="pulse-chip secondary">Governed metrics</span></div>""",
        unsafe_allow_html=True,
    )


def config_value(name: str, default: Any = None) -> Any:
    """Read configuration from environment variables or Streamlit-hosted secrets."""
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        # st.secrets raises when no secrets file or hosted secret store is configured.
        return default


def query_df(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(sql, params or []).fetchdf()


def query_one(sql: str, params: list[Any] | None = None) -> Any:
    df = query_df(sql, params)
    return None if df.empty else df.iloc[0, 0]


def company_metric_for_period(view: str, period: Any) -> pd.DataFrame:
    """Query one approved scorecard view with the scope its schema supports."""
    if view not in _SCORECARD_VIEWS:
        raise ValueError(f"Unsupported company scorecard view: {view}")
    scope = "" if view in _SCORECARD_GLOBAL_VIEWS else "department_id='ALL' AND "
    return query_df(f"SELECT value FROM {view} WHERE {scope}period=?", [period])


def quarantine_summary_for_run(run_id: str) -> pd.DataFrame:
    """Summarize quarantine records using the audit table's source_table column."""
    return query_df(
        """SELECT source_table AS table_name,reason,COUNT(*) AS rows
           FROM audit.quarantine WHERE run_id=? GROUP BY 1,2 ORDER BY 1,2""",
        [run_id],
    )


def prior_month_headcount(department_id: str, selected_period: Any) -> pd.DataFrame:
    """Return headcount for the latest available period before the selection."""
    return query_df(
        """SELECT SUM(value) AS value
           FROM metrics.m01_headcount
           WHERE department_id=?
             AND period=(SELECT MAX(period)
                         FROM metrics.m01_headcount
                         WHERE department_id=? AND period<?)""",
        [department_id, department_id, selected_period],
    )


def ensure_database() -> bool:
    """Build the local warehouse on first start, including hosted cold starts."""
    if DB_PATH.exists():
        return True
    data_dir=ROOT / "03_Data" / "csv"
    if not data_dir.exists():
        return False
    try:
        with st.spinner("Building the PulseIQ warehouse from the supplied CSVs…"):
            import etl
            etl.run(data_dir=data_dir,db_path=DB_PATH)
    except Exception as exc:
        st.error(f"Warehouse refresh failed: {type(exc).__name__}: {exc}")
        return False
    return DB_PATH.exists()


def _production_user() -> dict[str, Any] | None:
    credentials = str(config_value("PULSEIQ_USERS_JSON", ""))
    if not credentials:
        st.error("Login is required, but PULSEIQ_USERS_JSON is not configured. Add it through the hosting secret manager.")
        return None
    try:
        users = json.loads(credentials)
    except json.JSONDecodeError:
        st.error("PULSEIQ_USERS_JSON is not valid JSON. Check the hosting secret configuration.")
        return None
    if "pulseiq_user" in st.session_state:
        return st.session_state.pulseiq_user
    with st.sidebar.form("pulseiq-login"):
        username = st.text_input("Account")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in")
    if submit:
        record = users.get(username)
        valid=False
        try:
            if isinstance(record,dict) and record.get("password_salt_hex") and record.get("password_pbkdf2_hex"):
                salt=bytes.fromhex(str(record["password_salt_hex"]))
                actual=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt,600_000).hex()
                valid=hmac.compare_digest(actual,str(record["password_pbkdf2_hex"]))
        except (ValueError,binascii.Error):
            valid=False
        if valid:
            st.session_state.pulseiq_user = {
                "username": username, "role": str(record.get("role", "EXECUTIVE")).upper(),
                "department_id": record.get("department_id"), "team_id": record.get("team_id"),
                "is_authenticated": True,
            }
            st.rerun()
        st.sidebar.error("Account or password is not valid.")
    return st.session_state.get("pulseiq_user")


def require_user() -> dict[str, Any]:
    """Resolve a protected user or an explicitly labelled local demo persona."""
    apply_design_system()
    _render_sidebar_brand()
    st.sidebar.markdown("### Access")
    if str(config_value("PULSEIQ_REQUIRE_LOGIN", "0")).strip() == "1":
        user = _production_user()
        if not user:
            st.stop()
        _render_context(user)
        return user
    if DEMO_USERS.exists():
        roster = pd.read_csv(DEMO_USERS)
        choices = roster["username"].astype(str).tolist()
        chosen = st.sidebar.selectbox("Demo persona", choices, key="pulseiq_demo_persona")
        role = str(roster.loc[roster.username == chosen, "role"].iloc[0]).upper()
    else:
        chosen, role = "exec.demo", "EXECUTIVE"
    # The starter file describes roles but does not map real identities to teams.
    # These synthetic scopes demonstrate the policy only and are not authentication.
    if role == "HR":
        scope = {"department_id": config_value("PULSEIQ_DEMO_HR_DEPARTMENT", "D01"), "team_id": None}
    elif role == "MANAGER":
        scope = {"department_id": config_value("PULSEIQ_DEMO_MANAGER_DEPARTMENT", "D01"),
                 "team_id": config_value("PULSEIQ_DEMO_MANAGER_TEAM", "T01")}
    else:
        scope = {"department_id": None, "team_id": None}
    user = {"username": chosen, "role": role, **scope, "is_authenticated": False}
    st.sidebar.caption("Local role simulation; production login is enabled with PULSEIQ_REQUIRE_LOGIN=1.")
    _render_context(user)
    return user


def can_view_salary(user: dict[str, Any]) -> bool:
    return user.get("role") in {"ADMIN", "HR"}


def visible_departments(user: dict[str, Any], include_all: bool = True) -> list[str]:
    if user.get("role") == "EXECUTIVE":
        return ["ALL"]
    if user.get("role") == "MANAGER":
        return [str(user.get("department_id"))]
    if user.get("role") == "HR":
        return [str(user.get("department_id"))]
    data=query_df("SELECT DISTINCT department_id FROM metrics.dashboard_department_mix WHERE department_id<>'ALL' ORDER BY 1")
    values=data.department_id.astype(str).tolist() if not data.empty else []
    return (["ALL"] if include_all else [])+values


def department_picker(user: dict[str, Any], label: str = "Department") -> str:
    values=visible_departments(user)
    fixed=user.get("department_id")
    if user.get("role") == "EXECUTIVE":
        st.sidebar.caption("Executive view is company level.")
        return "ALL"
    if fixed:
        st.sidebar.caption(f"Scoped to {fixed} by the selected demo role.")
        return str(fixed)
    selected=st.sidebar.selectbox(label,values,key=f"scope_{label}") if values else "ALL"
    return selected


def period_picker(data: pd.DataFrame, label: str = "Report month", key: str = "period"):
    if data.empty or "period" not in data:
        return None
    values=sorted(pd.to_datetime(data.period).dropna().dt.date.unique())
    if not values:
        return None
    return st.sidebar.selectbox(label,values,index=len(values)-1,key=key)


def money(value: Any, currency: str = "INR") -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{currency} {float(value):,.0f}"


def pct(value: Any, already_pct: bool = True, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    number=float(value) if already_pct else float(value)*100
    return f"{number:.{digits}f}%"


def insight(text: str) -> None:
    safe_text = html.escape(text)
    st.markdown(
        f"""<div class="pulse-insight"><span class="pulse-insight-mark">IQ</span>
        <div><strong>Decision signal</strong><br>{safe_text}</div></div>""",
        unsafe_allow_html=True,
    )


def scoped_dept_clause(user: dict[str, Any], requested: str | None = None, column: str = "department_id"):
    role=user.get("role")
    fixed=user.get("department_id")
    if role == "EXECUTIVE":
        return "= ?", ["ALL"]
    if fixed:
        return "= ?", [fixed]
    value=requested or "ALL"
    return "= ?", [value]
