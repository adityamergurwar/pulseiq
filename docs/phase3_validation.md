# Phase 3 validation

Generated from the local DuckDB warehouse after rebuilding it from the supplied source CSVs.

## Task checks

| Check | Result | Evidence |
|---|---|---|
| Monthly P&L equation and coverage | PASS | 18 months; maximum tie-out difference INR 0.000000 |
| P&L monthly tie-out to official ledger key | PASS | 18 months; mismatches: {'total_revenue_and_other_income': 0, 'expenses': 0, 'net_profit': 0} |
| P&L excludes group accounts | PASS | P&L view filters active Profit & Loss detail accounts only. |
| P&L account mix, top vendors and margin hypotheses | PASS | account-mix mismatches 0; top ten, three monthly findings and three evidence-led causes are present. |
| Expense category and vendor totals | PASS | category mismatches 0; vendor mismatches 0 |
| Open receivable statuses and bucket reconciliation | PASS | as of 2026-09-30; open statuses ['OVERDUE', 'PARTIALLY_PAID', 'SENT']; ageing difference INR 0.00 |
| Client payment speed, overdue ranking and cash movement | PASS | all 28 clients with paid invoice history are included; days-to-pay mismatches 0; cash mismatches 0; overdue client groups 9; 75-day payer guidance True |
| Department impact reference comparison | PASS | 180/180 privacy-safe rows matched; 18 D00 rows suppressed; task differences in 19 groups are traced to quarantines. |
| Department comparison grain and measures | PASS | duplicate department-month rows 0; chart fields include cost, overtime, attrition and leave per head. |
| AI anomaly ranking, chart labels and forecast error coverage | PASS | 11 anomaly types ranked by reported risk; both AI charts labelled; 66 forecast rows; 0 actual overlaps. |
| Executive scorecard traceability, targets, rationales and links | PASS | 8/8 dictionary metrics return values; links True; A4 landscape print layout True. |
| Project README P&L headline tie-out | PASS | 18-month amounts match to INR 0.01; differences {'revenue': 0.0, 'other_income': 0.0, 'expenses': 0.0, 'net_profit': 0.0}; margin difference -0.00 pp. |

## P&L headline tie-out

- The governed P&L covers 18 ledger months. Across the snapshot: revenue INR 1,259,204,600.00; other income INR 1,725,452.00; expense INR 1,036,246,464.42; net profit INR 224,683,587.58; weighted operating margin 17.84%.
- Revenue plus other income, expense and net profit are checked month by month against the official PQ-09 ledger reconciliation file. Mismatches: {'total_revenue_and_other_income': 0, 'expenses': 0, 'net_profit': 0}.
- The supplied workbook README has P&L headline amounts: False. The project README now contains the 18-month P&L headline, which ties to the governed roll-up; each monthly value also ties independently to the official PQ-09 key.

## Receivables and forecast boundaries

- Open receivables total INR 139,394,278.00 at 2026-09-30; the specified open statuses are SENT, OVERDUE and PARTIALLY_PAID.
- The four requested ageing bands plus a separate not-due bucket reconcile to the total within INR 0.00.
- Forecast error cannot be estimated yet: 66 forecast rows and 0 overlapping actual rows in the supplied cutoff window.

## Department comparison

- The reference comparison has 198 rows; the view matches 180 privacy-safe rows. 18 single-person D00 rows are suppressed.
- All non-task fields match; task differences appear in 19 department-month groups because 20 invalid source task rows are quarantined. The underlying reference mismatch details are in the comparison output below.

| Reference field | Mismatching values |
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

## Overall

12/12 Phase 3 validation groups passed. Source-level seeded quality findings remain visible as documented review items; they are not represented as clean source data.
