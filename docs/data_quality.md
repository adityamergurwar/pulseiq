# Data quality gatekeeper

`audit.dq_results` stores every check's ID, name, severity, bad-row count, status and UTC run time. `audit.dq_check_details` stores row identifiers and explanations. All 14 checks run after every load. A test injects a bad example for each check and confirms the result changes from pass.

## Raw issue decisions

The validation vault contains 11 planted issue categories. All 11 were detected. The planted source rows are intentionally kept in `raw`; valid clean outputs either quarantine them or use an explicitly documented correction. Check counts can overlap and are not unique issue counts.

| Validation key | Detected by | Findings | Handling / effect |
|---|---|---:|---|
| DQ-01 post-exit attendance | DQ-C05 | 4 | Four rows are quarantined from attendance metrics. DQ-C06 also flags FA-X0004 because that same row has unpaid absence with no payroll LOP; it is an overlap, not a fifth post-exit row. |
| DQ-02 duplicate payroll | DQ-C03 | 2 | Duplicate rows are quarantined; clean payroll and ledger totals reconcile after exclusions. |
| DQ-03 orphan payroll employee | DQ-C04 | 2 | Orphan rows are quarantined; no employee names are exposed. |
| DQ-04 payroll-ledger mismatch | DQ-C01 | 1 planted June mismatch | Raw source remains unchanged. The clean layer applies a documented balanced-entry correction of INR 18,450; all 18 clean monthly periods reconcile within INR 0.01. Other raw monthly DQ-C01 differences are explained by the duplicate and orphan payroll rows. |
| DQ-05 overpaid invoice | DQ-C07 | 1 | Negative balance is identified; the open-receivables view includes only positive balances. |
| DQ-06 / DQ-07 invalid task dates | DQ-C09 | 20 | Twelve negative cycle-time records and eight Done rows without dates are quarantined from task metrics. |
| DQ-08 reversed leave dates | DQ-C10 | 2 | Warning remains visible in the audit results; raw dates are preserved. |
| DQ-09 stale risk batch | DQ-C11 | 5 | The older batch is identified; grouped risk views use the latest as-of date only. |
| DQ-10 expense arithmetic | DQ-C08 | 1 | The INR 500 component mismatch remains visible in DQ output; the ledger-based P&L does not use this expense row as its source. |
| DQ-11 employee history overlap | DQ-C12 | 1 | The SCD range is repaired in the conformed warehouse and recorded in `audit.scd_repairs`; raw history is preserved. |

## Severity and release gate

Critical raw findings are `FAIL` and warning findings are `WARN`; the app does not hide them or rewrite source evidence. A raw DQ failure is not a failed check implementation: it means the seeded source condition was found. The clean payroll reconciliation and zero warehouse orphans are reported separately. The dashboard displays `REVIEW REQUIRED` until an owner reviews the source findings. Do not represent the data as cleared for a public release without that review.

## Contract and schema scope

The source dictionary checks type and requiredness for 297 columns across 23 operational dimension/fact tables. `data_contracts.csv` adds explicit allowed-value, range, identifier and cross-row rules for the four feeds it covers. Missing contracted columns stop the run; unexpected columns are retained and reported for review. See [contract notes](contract_notes.md).
