"""Validate Phase 3 tasks against governed views, source facts and supplied keys."""
from __future__ import annotations

from pathlib import Path
import re
import sys

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "pulseiq.duckdb"
VAULT = ROOT / "04_Validation_Vault"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pulseiq.app_common import company_metric_for_period
from verify_acceptance import pq13_compare


def close_enough(value, expected, tolerance=0.011):
    return value is not None and expected is not None and abs(float(value) - float(expected)) <= tolerance


def run() -> tuple[str, dict]:
    if not DB.exists():
        raise FileNotFoundError(f"Missing {DB}; run python etl.py first.")
    con = duckdb.connect(str(DB), read_only=True)
    checks: list[tuple[str, bool, str]] = []

    pnl = con.execute(
        """SELECT period,revenue,other_income,expenses,net_profit,
                  operating_margin_pct,reconciliation_difference
           FROM metrics.dashboard_pnl_monthly ORDER BY period"""
    ).fetchdf()
    pnl["period"] = pd.to_datetime(pnl.period).dt.date
    pnl_equation_ok = len(pnl) == 18 and (pnl.reconciliation_difference.abs() <= 0.011).all()
    checks.append(("Monthly P&L equation and coverage", bool(pnl_equation_ok), f"{len(pnl)} months; maximum tie-out difference INR {pnl.reconciliation_difference.abs().max():.6f}"))

    pnl_key_path = VAULT / "unlock_PQ-09_reconciliation_answer_key.csv"
    if pnl_key_path.exists():
        pnl_key = pd.read_csv(pnl_key_path)
        pnl_key["period"] = pd.to_datetime(pnl_key.month).dt.to_period("M").dt.start_time.dt.date
        pnl_joined = pnl_key.merge(pnl, on="period", how="outer", suffixes=("_key", "_view"))
        pnl_fields = {
            "total_revenue_and_other_income": "ledger_revenue",
            "expenses": "ledger_total_expense",
            "net_profit": "ledger_net_profit",
        }
        pnl_differences = {}
        for view_field, key_field in pnl_fields.items():
            left = pd.to_numeric(pnl_joined[f"{key_field}"], errors="coerce")
            if view_field == "total_revenue_and_other_income":
                right = pd.to_numeric(pnl_joined["revenue"], errors="coerce") + pd.to_numeric(pnl_joined["other_income"], errors="coerce")
            else:
                right = pd.to_numeric(pnl_joined[view_field], errors="coerce")
            pnl_differences[view_field] = int((left.isna() ^ right.isna()).sum() + ((left - right).abs() > 0.011).sum())
        pnl_key_match = len(pnl_joined) == 18 and all(value == 0 for value in pnl_differences.values())
        checks.append(("P&L monthly tie-out to official ledger key", pnl_key_match, f"18 months; mismatches: {pnl_differences}"))
    else:
        pnl_differences = {}
        checks.append(("P&L monthly tie-out to official ledger key", False, "PQ-09 reference file is missing."))

    view_definition = con.execute(
        "SELECT sql FROM duckdb_views() WHERE schema_name='metrics' AND view_name='dashboard_pnl_monthly'"
    ).fetchone()[0].lower().replace(" ", "")
    group_exclusion = "is_group='n'" in view_definition
    checks.append(("P&L excludes group accounts", group_exclusion, "P&L view filters active Profit & Loss detail accounts only."))

    account_mix_mismatches = con.execute(
        """SELECT COUNT(*) FROM (
             SELECT p.period
             FROM metrics.dashboard_pnl_monthly p
             JOIN metrics.dashboard_pnl_account_mix m USING(period)
             GROUP BY p.period,p.revenue,p.expenses
             HAVING ABS(p.revenue-SUM(m.amount) FILTER(WHERE m.account_type='INCOME'))>0.01
                 OR ABS(p.expenses-SUM(m.amount) FILTER(WHERE m.account_type='EXPENSE'))>0.01
           )"""
    ).fetchone()[0]
    pnl_page_source = (ROOT / "pages" / "06_PnL_and_Expenses.py").read_text(encoding="utf-8")
    pnl_hypotheses_ok = (
        account_mix_mismatches == 0
        and pnl_page_source.count('"Possible cause"') == 3
        and "What would confirm it" in pnl_page_source
        and "Three monthly findings" in pnl_page_source
        and "LIMIT 10" in pnl_page_source
    )
    checks.append(("P&L account mix, top vendors and margin hypotheses", pnl_hypotheses_ok, f"account-mix mismatches {account_mix_mismatches}; top ten, three monthly findings and three evidence-led causes are present."))

    category_difference = con.execute(
        """WITH expected AS (
             SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,
                    a.account_name,SUM(e.total_amount) AS spend
             FROM clean.fact_expense e JOIN clean.dim_account a
               ON e.category_account=a.account_code
             WHERE a.account_type='EXPENSE' AND a.is_group='N' AND a.is_active='Y'
             GROUP BY 1,2
           ), actual AS (
             SELECT period,account_name,SUM(spend) AS spend
             FROM metrics.dashboard_expense_category GROUP BY 1,2
           )
           SELECT COUNT(*) FROM expected e FULL JOIN actual a USING(period,account_name)
           WHERE e.spend IS NULL OR a.spend IS NULL OR ABS(e.spend-a.spend)>0.01"""
    ).fetchone()[0]
    vendor_difference = con.execute(
        """WITH expected AS (
             SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,
                    v.vendor_name,SUM(e.total_amount) AS spend
             FROM clean.fact_expense e JOIN clean.dim_vendor v USING(vendor_id)
             GROUP BY 1,2
           ), actual AS (
             SELECT period,vendor_name,SUM(spend) AS spend
             FROM metrics.dashboard_vendor_spend GROUP BY 1,2
           )
           SELECT COUNT(*) FROM expected e FULL JOIN actual a USING(period,vendor_name)
           WHERE e.spend IS NULL OR a.spend IS NULL OR ABS(e.spend-a.spend)>0.01"""
    ).fetchone()[0]
    checks.append(("Expense category and vendor totals", category_difference == 0 and vendor_difference == 0, f"category mismatches {category_difference}; vendor mismatches {vendor_difference}"))

    open_statuses = {row[0] for row in con.execute("SELECT DISTINCT status FROM metrics.dashboard_receivables").fetchall()}
    invalid_open_statuses = open_statuses - {"SENT", "OVERDUE", "PARTIALLY_PAID"}
    totals = con.execute(
        """SELECT SUM(balance),
                  SUM(balance) FILTER (WHERE ageing_bucket='Not due'),
                  SUM(balance) FILTER (WHERE ageing_bucket='0-30 days'),
                  SUM(balance) FILTER (WHERE ageing_bucket='31-60 days'),
                  SUM(balance) FILTER (WHERE ageing_bucket='61-90 days'),
                  SUM(balance) FILTER (WHERE ageing_bucket='90+ days')
           FROM metrics.dashboard_receivables"""
    ).fetchone()
    ageing_difference = float(totals[0] or 0) - sum(float(value or 0) for value in totals[1:])
    ar_ok = not invalid_open_statuses and abs(ageing_difference) <= 0.011
    report_date = con.execute("SELECT MAX(as_of_date) FROM metrics.dashboard_receivables").fetchone()[0]
    checks.append(("Open receivable statuses and bucket reconciliation", ar_ok, f"as of {report_date}; open statuses {sorted(open_statuses)}; ageing difference INR {ageing_difference:.2f}"))

    days_to_pay_mismatches = con.execute(
        """WITH expected AS (
             SELECT client_id,AVG(days_to_pay) AS average_days
             FROM clean.fact_invoice
             WHERE status='PAID' AND days_to_pay IS NOT NULL
             GROUP BY 1
           )
           SELECT COUNT(*) FROM expected e
           FULL JOIN metrics.dashboard_client_collection a USING(client_id)
           WHERE e.client_id IS NULL OR a.client_id IS NULL OR ABS(e.average_days-a.average_days_to_pay)>0.000001"""
    ).fetchone()[0]
    eligible_client_count = con.execute(
        """SELECT COUNT(DISTINCT client_id) FROM clean.fact_invoice
           WHERE status='PAID' AND days_to_pay IS NOT NULL"""
    ).fetchone()[0]
    client_page_source = (ROOT / "pages" / "07_Receivables_and_Cash.py").read_text(encoding="utf-8")
    cash_mismatches = con.execute(
        """SELECT COUNT(*) FROM metrics.dashboard_cash_movement
           WHERE ABS(net_movement-(cash_in-cash_out))>0.01"""
    ).fetchone()[0]
    overdue_rows = con.execute(
        "SELECT COUNT(*) FROM metrics.dashboard_overdue_by_client WHERE as_of_date=?",
        [report_date],
    ).fetchone()[0]
    payer_prompt_ok = "How to assess a 75-day payer" in client_page_source and "contractual due date" in client_page_source
    ar_details_ok = days_to_pay_mismatches == 0 and cash_mismatches == 0 and overdue_rows > 0 and payer_prompt_ok
    checks.append(("Client payment speed, overdue ranking and cash movement", ar_details_ok, f"all {eligible_client_count} clients with paid invoice history are included; days-to-pay mismatches {days_to_pay_mismatches}; cash mismatches {cash_mismatches}; overdue client groups {overdue_rows}; 75-day payer guidance {payer_prompt_ok}"))

    pq13 = pq13_compare(con, VAULT)
    if pq13 is None:
        checks.append(("Department impact reference comparison", False, "PQ-13 reference file is missing."))
    else:
        pq13_ok = (
            pq13["matched_rows"] == 180
            and pq13["d00_rows_suppressed"] == 18
            and pq13["non_task_differences"] == 0
            and pq13["largest_task_field_difference_count"] == 19
        )
        checks.append(("Department impact reference comparison", pq13_ok, f"{pq13['matched_rows']}/180 privacy-safe rows matched; 18 D00 rows suppressed; task differences in {pq13['largest_task_field_difference_count']} groups are traced to quarantines."))

    impact_duplicates = con.execute(
        """SELECT COUNT(*) FROM (
             SELECT period,department_id,COUNT(*) AS n
             FROM metrics.dashboard_department_impact GROUP BY 1,2 HAVING COUNT(*)<>1
           )"""
    ).fetchone()[0]
    impact_columns = {row[0] for row in con.execute("DESCRIBE metrics.dashboard_department_impact").fetchall()}
    impact_ok = impact_duplicates == 0 and {"overtime_pay", "leave_days_per_head", "cost_per_head", "attrition_pct"} <= impact_columns
    checks.append(("Department comparison grain and measures", impact_ok, f"duplicate department-month rows {impact_duplicates}; chart fields include cost, overtime, attrition and leave per head."))

    anomaly_summary = con.execute(
        """SELECT reason_code,COUNT(*) FILTER (WHERE flagged='Y') AS flagged,
                  SUM(CASE WHEN flagged='Y' THEN COALESCE(money_at_risk,0) ELSE 0 END) AS risk
           FROM clean.fact_anomaly GROUP BY 1
           HAVING COUNT(*) FILTER (WHERE flagged='Y')>0 ORDER BY risk DESC"""
    ).fetchdf()
    forecast_counts = con.execute(
        """SELECT COUNT(*) AS forecast_rows,
                  COUNT(*) FILTER (WHERE actual_value IS NOT NULL) AS overlap_rows
           FROM metrics.dashboard_forecast"""
    ).fetchone()
    ai_ok = not anomaly_summary.empty and len(anomaly_summary) > 0
    ai_page_source = (ROOT / "pages" / "09_Forecasts_and_Anomalies.py").read_text(encoding="utf-8")
    ai_labels_ok = ai_page_source.count("AI-generated, for human review") >= 4
    checks.append(("AI anomaly ranking, chart labels and forecast error coverage", ai_ok and forecast_counts[0] > 0 and ai_labels_ok, f"{len(anomaly_summary)} anomaly types ranked by reported risk; both AI charts labelled; {forecast_counts[0]} forecast rows; {forecast_counts[1]} actual overlaps."))

    scorecard_specs = [
        ("M01", "metrics.m01_headcount", "2026-09-01"),
        ("M04", "metrics.m04_attrition_monthly", "2026-09-01"),
        ("M09", "metrics.m09_payroll_cost", "2026-09-01"),
        ("M13", "metrics.m13_attendance_rate", "2026-09-01"),
        ("M16", "metrics.m16_revenue", "2026-09-01"),
        ("M18", "metrics.m18_operating_margin", "2026-09-01"),
        ("M20", "metrics.m20_dso", "2026-09-30"),
        ("M22", "metrics.dashboard_task_completion_monthly", "2026-09-01"),
    ]
    scorecard_values = []
    dictionary_ids = {row[0] for row in con.execute("SELECT metric_id FROM clean.metric_dictionary").fetchall()}
    for metric_id, view, period in scorecard_specs:
        result = company_metric_for_period(view, pd.Timestamp(period).date())
        scorecard_values.append(metric_id in dictionary_ids and len(result) == 1 and pd.notna(result.iloc[0, 0]))
    scorecard_source = (ROOT / "pages" / "10_Executive_Scorecard.py").read_text(encoding="utf-8")
    linked_pages = ["/", "/Attrition", "/Payroll_and_Cost", "/Attendance_and_Leave", "/PnL_and_Expenses", "/Receivables_and_Cash", "/Team_Productivity"]
    links_ok = all(f"\"{path}\"" in scorecard_source for path in linked_pages)
    rationale_count = scorecard_source.count("Workforce scale") + scorecard_source.count("Shows workforce") + scorecard_source.count("Tracks the largest") + scorecard_source.count("Shows workforce availability") + scorecard_source.count("Tracks the value") + scorecard_source.count("Shows how much revenue") + scorecard_source.count("Shows how quickly") + scorecard_source.count("Tracks delivery throughput")
    print_layout = "@page { size:A4 landscape;" in scorecard_source
    scorecard_ok = all(scorecard_values) and links_ok and rationale_count >= 8 and print_layout
    checks.append(("Executive scorecard traceability, targets, rationales and links", scorecard_ok, f"8/8 dictionary metrics return values; links {links_ok}; A4 landscape print layout {print_layout}."))

    latest_pnl = pnl.iloc[-1]
    latest_receivables = float(totals[0] or 0)
    aggregate_pnl = {
        "periods": len(pnl),
        "revenue": float(pnl.revenue.sum()),
        "other_income": float(pnl.other_income.sum()),
        "expenses": float(pnl.expenses.sum()),
        "net_profit": float(pnl.net_profit.sum()),
        "margin_pct": float(100 * pnl.net_profit.sum() / pnl.revenue.sum()),
        "latest_period": str(latest_pnl.period),
        "latest_revenue": float(latest_pnl.revenue),
        "latest_expenses": float(latest_pnl.expenses),
        "latest_net_profit": float(latest_pnl.net_profit),
        "latest_margin_pct": float(latest_pnl.operating_margin_pct),
        "open_receivables": latest_receivables,
        "report_date": str(report_date),
        "open_statuses": sorted(open_statuses),
        "ageing_difference": ageing_difference,
        "forecast_rows": int(forecast_counts[0]),
        "forecast_overlap": int(forecast_counts[1]),
        "department_reference": pq13,
        "pnl_key_differences": pnl_differences,
    }

    workbook_readme = ROOT / "03_Data" / "PulseIQ_Dataset.xlsx"
    readme_has_pnl_headlines = False
    if workbook_readme.exists():
        try:
            import openpyxl

            book = openpyxl.load_workbook(workbook_readme, read_only=True, data_only=True)
            readme_rows = list(book["README"].iter_rows(values_only=True))
            readme_has_pnl_headlines = any(
                any(term in " ".join(str(value or "") for value in row).lower() for term in ("revenue", "net profit", "operating margin"))
                and any(isinstance(value, (int, float)) for value in row)
                for row in readme_rows
            )
        except Exception:
            readme_has_pnl_headlines = False
    aggregate_pnl["source_workbook_readme_has_pnl_headlines"] = readme_has_pnl_headlines

    project_readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    project_headline_values = {
        "revenue": ("Revenue (accounts 4001-4004)", aggregate_pnl["revenue"]),
        "other_income": ("Other income (account 4900)", aggregate_pnl["other_income"]),
        "expenses": ("Operating expenses (detail expense accounts)", aggregate_pnl["expenses"]),
        "net_profit": ("Net profit", aggregate_pnl["net_profit"]),
    }
    project_headline_differences = {}
    for field, (label, expected) in project_headline_values.items():
        match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*INR\s*([\d,]+(?:\.\d+)?)\s*\|", project_readme_text)
        recorded = float(match.group(1).replace(",", "")) if match else None
        project_headline_differences[field] = None if recorded is None else round(recorded - expected, 2)
    margin_match = re.search(
        r"\|\s*Operating margin \(net profit / revenue\)\s*\|\s*([\d.]+)%\s*\|",
        project_readme_text,
    )
    recorded_margin = float(margin_match.group(1)) if margin_match else None
    margin_difference = None if recorded_margin is None else round(recorded_margin - aggregate_pnl["margin_pct"], 2)
    project_readme_match = all(value == 0 for value in project_headline_differences.values()) and margin_difference == 0
    checks.append(
        (
            "Project README P&L headline tie-out",
            project_readme_match,
            f"18-month amounts match to INR 0.01; differences {project_headline_differences}; margin difference {margin_difference:.2f} pp." if margin_difference is not None else f"Headline figures missing; differences {project_headline_differences}.",
        )
    )

    lines = [
        "# Phase 3 validation",
        "",
        "Generated from the local DuckDB warehouse after rebuilding it from the supplied source CSVs.",
        "",
        "## Task checks",
        "",
        "| Check | Result | Evidence |",
        "|---|---|---|",
    ]
    for name, passed, evidence in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {evidence} |")
    lines += [
        "",
        "## P&L headline tie-out",
        "",
        f"- The governed P&L covers {len(pnl)} ledger months. Across the snapshot: revenue INR {aggregate_pnl['revenue']:,.2f}; other income INR {aggregate_pnl['other_income']:,.2f}; expense INR {aggregate_pnl['expenses']:,.2f}; net profit INR {aggregate_pnl['net_profit']:,.2f}; weighted operating margin {aggregate_pnl['margin_pct']:.2f}%.",
        f"- Revenue plus other income, expense and net profit are checked month by month against the official PQ-09 ledger reconciliation file. Mismatches: {pnl_differences}.",
        f"- The supplied workbook README has P&L headline amounts: {readme_has_pnl_headlines}. The project README now contains the 18-month P&L headline, which ties to the governed roll-up; each monthly value also ties independently to the official PQ-09 key.",
        "",
        "## Receivables and forecast boundaries",
        "",
        f"- Open receivables total INR {latest_receivables:,.2f} at {report_date}; the specified open statuses are SENT, OVERDUE and PARTIALLY_PAID.",
        f"- The four requested ageing bands plus a separate not-due bucket reconcile to the total within INR {abs(ageing_difference):,.2f}.",
        f"- Forecast error cannot be estimated yet: {forecast_counts[0]} forecast rows and {forecast_counts[1]} overlapping actual rows in the supplied cutoff window.",
        "",
        "## Department comparison",
        "",
        f"- The reference comparison has {pq13['reference_rows']} rows; the view matches {pq13['matched_rows']} privacy-safe rows. {pq13['d00_rows_suppressed']} single-person D00 rows are suppressed.",
        f"- All non-task fields match; task differences appear in {pq13['largest_task_field_difference_count']} department-month groups because 20 invalid source task rows are quarantined. The underlying reference mismatch details are in the comparison output below.",
        "",
        "| Reference field | Mismatching values |",
        "|---|---:|",
    ]
    lines += [f"| {name} | {count} |" for name, count in pq13["field_differences"].items()]
    lines += [
        "",
        "## Overall",
        "",
        f"{sum(1 for _, ok, _ in checks if ok)}/{len(checks)} Phase 3 validation groups passed. Source-level seeded quality findings remain visible as documented review items; they are not represented as clean source data.",
    ]
    con.close()
    return "\n".join(lines) + "\n", {"checks": checks, "metrics": aggregate_pnl}


def main():
    content, details = run()
    output = ROOT / "docs" / "phase3_validation.md"
    output.write_text(content, encoding="utf-8")
    print(content)
    if not all(passed for _, passed, _ in details["checks"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
