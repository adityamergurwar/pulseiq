import pandas as pd
import streamlit as st

from pulseiq.app_common import DB_PATH, ensure_database, quarantine_summary_for_run, query_df, require_user

st.title("Data quality, contracts and lineage")
st.caption("Refresh status, source quality issues, quarantine counts and warehouse reconciliation evidence.")
if not ensure_database():
    st.warning("Run python etl.py first.")
    st.stop()
user=require_user()

fresh=query_df("SELECT * FROM metrics.dashboard_data_freshness")
if not fresh.empty:
    f=fresh.iloc[0]
    a,b,c=st.columns(3)
    a.metric("Latest refresh",pd.Timestamp(f.last_successful_refresh).strftime("%d %b %Y %H:%M UTC"))
    b.metric("Data cut-off",pd.Timestamp(f.data_cutoff).strftime("%d %b %Y"))
    c.metric("Freshness",str(f.status))

latest=query_df("SELECT run_id FROM audit.etl_run_log ORDER BY started_at DESC LIMIT 1")
if latest.empty:
    st.error("No ETL run has been recorded.")
    st.stop()
run_id=str(latest.iloc[0,0])
results=query_df("SELECT check_id,check_name,table_name,severity,bad_rows,status FROM audit.dq_results WHERE run_id=? ORDER BY check_id",[run_id])
bad=int(results.bad_rows.sum()) if not results.empty else 0
failed=int((results.status=="FAIL").sum()) if not results.empty else 0
if failed:
    st.warning(f"Release gate: REVIEW REQUIRED. {failed} critical checks have source rows that need review. {bad:,} check-level findings are visible below; checks may overlap on the same source issue.")
else:
    st.success("No critical check is currently failing.")
st.dataframe(results,use_container_width=True,hide_index=True)

st.subheader("Row-count reconciliation")
counts=query_df("SELECT table_name,rows_in,rows_passed,rows_quarantined,rows_in-rows_passed-rows_quarantined AS unexplained FROM audit.load_summary WHERE run_id=? ORDER BY table_name",[run_id])
if not counts.empty:
    st.dataframe(counts,use_container_width=True,hide_index=True)
    if int(counts.unexplained.abs().sum())==0:
        st.success("Every source table satisfies rows in = rows passed + rows quarantined.")

quarantine=quarantine_summary_for_run(run_id)
if not quarantine.empty:
    st.subheader("Quarantined rows by reason")
    st.caption("Record-level identifiers are withheld here; the audit table retains the source row and reason for authorized investigation.")
    st.dataframe(quarantine,use_container_width=True,hide_index=True)

st.subheader("Warehouse integrity")
orphans=query_df("SELECT fact_table,relationship,orphan_rows,disposition FROM audit.orphan_results ORDER BY fact_table,relationship")
st.dataframe(orphans,use_container_width=True,hide_index=True)
if not orphans.empty and int(orphans.orphan_rows.sum())==0:
    st.success("All declared warehouse relationships have zero unmatched keys.")
recon=query_df("SELECT period,payroll_cost,ledger_payroll_cost,difference,status FROM audit.payroll_ledger_reconciliation_clean ORDER BY period")
if not recon.empty:
    st.subheader("Clean payroll-to-ledger reconciliation")
    st.caption("The raw ledger remains unchanged. The conformed warehouse contains a documented correction for DQ-04, reducing equal salary and payroll-payable sides by INR 18,450 in June 2026.")
    st.dataframe(recon.style.format({"payroll_cost":"{:,.2f}","ledger_payroll_cost":"{:,.2f}","difference":"{:,.4f}"}),use_container_width=True,hide_index=True)
    st.metric("Reconciled periods",f"{int((recon.status=='PASS').sum())} / {len(recon)}")

st.subheader("Declared feed contracts")
contracts=query_df("SELECT table_name,column_name,data_type,is_nullable,allowed_values,minimum_value,maximum_value FROM clean.data_contracts ORDER BY table_name,column_name")
st.caption("The supplied contract file declares four contracted feeds. The loader also applies the dataset dictionary's type/nullability checks to all source feeds; uncovered business rules remain in the DQ catalog and report.")
st.dataframe(contracts,use_container_width=True,hide_index=True)

st.subheader("SCD and metric-layer release notes")
repairs=query_df("SELECT employee_id,employee_key,source_valid_to,repaired_valid_to,reason FROM audit.scd_repairs")
if not repairs.empty:
    st.dataframe(repairs,use_container_width=True,hide_index=True)
st.markdown("- `raw` preserves the delivered CSV values.\n- `clean` contains contract-passing rows; failures remain in `audit.quarantine`.\n- `warehouse` applies the documented effective-date and balanced ledger corrections.\n- `metrics` owns the M01–M28 definitions and dashboard-safe aggregates.")
st.caption("See docs/lineage.md for raw-to-dashboard lineage and docs/data_quality.md for the planted issue comparison.")
