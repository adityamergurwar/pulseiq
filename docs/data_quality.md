# Data quality gatekeeper

`audit.dq_results` stores check ID, name, severity, bad-row count, status, and UTC run time. The catalog's 14 controls are run in `etl.py` on every full load. Critical failures are blockers for a release; warning checks require an owner and documented disposition. The current implementation reports all statuses; the operator should not publish a dashboard when any critical check fails.

| Check | Risk detected | Severity |
|---|---|---|
| DQ-C01 | Payroll employer cost differs from salary ledger postings | Critical |
| DQ-C02 | Unbalanced journal entry | Critical |
| DQ-C03 | Duplicate employee payroll month | Critical |
| DQ-C04 | Payroll employee missing from employee dimension | Critical |
| DQ-C05 | Attendance occurs after recorded employee exit | Warning |
| DQ-C06 | Unpaid attendance absence lacks payroll LOP deduction | Warning |
| DQ-C07 | Invoice payment exceeds invoice total or negative balance | Warning |
| DQ-C08 | Expense total differs from amount plus GST | Warning |
| DQ-C09 | Task completion dates/status conflict | Warning |
| DQ-C10 | Leave end precedes leave start | Warning |
| DQ-C11 | Attrition-risk prediction is stale relative to latest batch | Warning |
| DQ-C12 | Employee effective-dated records overlap | Critical |
| DQ-C13 | Latest ETL run is older than 24 hours | Critical |
| DQ-C14 | Headcount cell falls below the five-person privacy floor | Critical |

The source catalog uses some legacy column names. The ETL maps the intent to the delivered schema; the exact SQL and counts are the auditable implementation. A future iteration should parameterize the privacy threshold from each metric's `minimum_group_size` rather than applying a blanket threshold of five.
