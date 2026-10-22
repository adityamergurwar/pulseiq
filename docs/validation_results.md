# Local acceptance evidence

Generated: 2026-10-22 12:23

## Pipeline and warehouse

- Latest run: `c47e18eb-cba4-488e-b4cb-21241629c770`; source tables: 29; unexplained row-count difference: 0.
- Warehouse declared relationships with orphans: 0.
- Governed metric views: 28; all have rows: True.
- M28 rows: 66; measured values: 0 (actuals start after supplied forecast horizon).

## Seeded issue detection

| Check | Status | Findings |
|---|---:|---:|
| DQ-C01 | FAIL | 5 |
| DQ-C02 | PASS | 0 |
| DQ-C03 | FAIL | 2 |
| DQ-C04 | FAIL | 2 |
| DQ-C05 | WARN | 4 |
| DQ-C06 | WARN | 1 |
| DQ-C07 | WARN | 1 |
| DQ-C08 | WARN | 1 |
| DQ-C09 | WARN | 20 |
| DQ-C10 | WARN | 2 |
| DQ-C11 | WARN | 5 |
| DQ-C12 | FAIL | 1 |
| DQ-C13 | PASS | 0 |
| DQ-C14 | PASS | 0 |

DQ-C06 flags the same post-exit attendance row already identified by DQ-C05; it is not an additional planted issue. The clean warehouse quarantines four post-exit attendance rows, four invalid payroll rows, two reversed-date leave rows, one expense arithmetic mismatch and 20 invalid task rows. The raw source stays intact. The SCD overlap and DQ-04 ledger mismatch are corrected in the conformed warehouse and recorded in audit tables.

## Hand calculations

| Check | Independently calculated | Governed view | Result |
|---|---:|---:|---|
| M01 active SCD headcount, D01 | 167.000000 | 167.000000 | PASS |
| M07 gross pay, D01 | 20,720,901.380000 | 20,720,901.380000 | PASS |
| M13 weighted attendance rate, D01 | 0.961784 | 0.961784 | PASS |
| M17 ledger net profit | 14,985,979.130000 | 14,985,979.130000 | PASS |
| M20 event-based DSO | 47.997728 | 47.997728 | PASS |
| M22 task completion, T01 / SP-01 | 90.909091 | 90.909091 | PASS |
| M24 velocity, T01 / SP-01 | 162.000000 | 162.000000 | PASS |
| M25 cycle time, T01 / SP-01 | 4.640000 | 4.640000 | PASS |
| M24 velocity, T02 / SP-01 | 210.000000 | 210.000000 | PASS |
| M25 cycle time, T02 / SP-01 | 4.793651 | 4.793651 | PASS |
| PQ-10 budget variance, D01 | 214,404.240000 | 214,404.240000 | PASS |
| PQ-10 budget variance, D02 | -42,581.210000 | -42,581.210000 | PASS |
| PQ-10 budget variance, D03 | 30,889.620000 | 30,889.620000 | PASS |

## PQ-09 reconciliation answer key

- Compared 18 reference months; payroll, ledger, cash and receivables rows matched: True.
- Largest clean payroll-to-ledger difference: INR 0.00000004 (acceptance tolerance INR 0.01).

| Field | Mismatching months |
|---|---:|
| employees_paid | 0 |
| payroll_gross_pay | 0 |
| payroll_net_pay | 0 |
| payroll_employer_cost | 0 |
| ledger_salary_related_expense | 0 |
| ledger_revenue | 0 |
| ledger_total_expense | 0 |
| ledger_net_profit | 0 |
| bank_closing_balance | 0 |
| receivables_closing_balance | 0 |
| payroll_vs_ledger_difference | 0 |

## PQ-13 department-month comparison

- Reference contains 198 rows. 18 single-person D00 reference rows are withheld; 180 department-month rows match the privacy-safe view.
- All non-task fields match within source precision: True.
- Task differences occur in 19 or fewer department-month groups and match the locations of the 20 quarantined invalid task rows.

| Reference field | Differences after privacy suppression |
|---|---:|
| employer_cost | 0 |
| gross_pay | 0 |
| overtime_pay | 0 |
| employees_paid | 0 |
| overtime_hours | 0 |
| late_arrivals | 0 |
| attendance_rate | 0 |
| headcount_end | 0 |
| hires | 0 |
| exits | 0 |
| attrition_rate_monthly_pct | 0 |
| tasks | 19 |
| tasks_done | 19 |
| story_points_done | 19 |
| task_completion_rate_pct | 13 |
| cost_per_head | 0 |
| overtime_share_pct | 0 |

## Release interpretation

- DQ checks: 14 automated; 4 critical check(s) fail against the intentionally seeded raw issues and 7 warning check(s) are recorded.
- Release gate remains REVIEW REQUIRED until a human reviews source findings. Clean-layer reconciliation and all calculations above can pass while raw DQ checks still report planted issues.
- Forecast MAPE is not estimable because actuals end in September 2026 and the supplied forecast starts in October 2026.

## Build verification

- Unit/regression suite: 13 tests passed on 2026-10-22, including role access, department scope, host-secret lookup, the dashboard query regression, and seeded-row quarantine behavior.
- Docker: rebuilt all three Python 3.11 service images and ran the warehouse initializer in an isolated Compose project. It exited successfully with 29/29 source-table reconciliations, 31 documented quarantines, and 0 declared orphans. The seeded raw findings intentionally leave the release gate at `REVIEW REQUIRED`. The isolated validation volume was removed after the check; the Compose interpolation used only an empty placeholder, not production credentials.
- Monthly workbook: generated from the latest ETL run, imported, recalculated and exported with Artifact Tool. It contains 9 sheets and 9 tables; the overview matches September 2026 governed values and the quality tab shows the source findings and 31 clean-layer quarantines. Formula-error scan found no matches. The overview and quality views were rendered and inspected.
- Reports: regenerated the September management pack (4 pages) and Phase 1 evidence report (3 pages) from the latest evidence. All pages were rendered and visually inspected.
- Local app, Docker, tests and report generation are verified in this workspace. The first remote GitHub Actions run and production authentication remain unverified until the repository/workspace account actions in `docs/deployment.md` are completed.
