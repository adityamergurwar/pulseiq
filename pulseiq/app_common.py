"""Shared Streamlit access rules, data access and UI helpers."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import binascii
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("PULSEIQ_DB_PATH", ROOT / "pulseiq.duckdb"))
DEMO_USERS = ROOT / "05_Starter" / "demo_users.csv"


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
    st.sidebar.markdown("### Access")
    if str(config_value("PULSEIQ_REQUIRE_LOGIN", "0")).strip() == "1":
        user = _production_user()
        if not user:
            st.stop()
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
    st.markdown(f"**Insight:** {text}")


def scoped_dept_clause(user: dict[str, Any], requested: str | None = None, column: str = "department_id"):
    role=user.get("role")
    fixed=user.get("department_id")
    if role == "EXECUTIVE":
        return "= ?", ["ALL"]
    if fixed:
        return "= ?", [fixed]
    value=requested or "ALL"
    return "= ?", [value]
