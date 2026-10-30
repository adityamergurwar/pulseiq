# PulseIQ Phase 2 validation

Phase 2 covers tasks 6-10: attendance and leave, attrition, team productivity, payroll cost, and budget/KPI targets. The current warehouse snapshot ends 2026-09-30.

## Automated checks

- Unit and regression suite: 18 tests passed.
- ETL acceptance: 29 source tables; 0 unexplained row-count differences; 0 declared relationship orphans.
- Governed layer: 28 of 28 metric views contain results.
- Team productivity coverage: 16 teams across 38 sprints.
- PQ-09 answer key: all 18 reference months match; maximum clean payroll-to-ledger difference is INR 0.00000004, below INR 0.01 tolerance.
- PQ-10 manual variance checks: D01, D02, and D03 match the independently calculated actual-minus-budget results.

## Task evidence

| Task | Verified evidence |
|---|---|
| 6 - Attendance and leave | M13 equals present days plus half unpaid days divided by scheduled working days, weighted across employees. Weekends and public holidays are excluded from scheduled days. Company-wide lowest rates: May 2026, 92.89% (1 public holiday, 545 approved leave days); January 2026, 93.29% (3 holidays, including 1 Friday/Monday holiday, 573 leave days); April 2026, 93.35% (2 holidays, including 1 Friday holiday, 405 leave days). Calendar overlap is labeled as context, not a proven cause. A department follow-up identifies the largest month-over-month rate decline: D10, down 10.83 percentage points in May 2026. |
| 7 - Attrition | September 2026 company snapshot: 3 observed exits, 2 voluntary and 1 other; monthly attrition is 0.70% of starting headcount. The baseline risk snapshot is explicitly separate and labeled as a prediction. Exit-reason/tenure groups below five and risk bands below ten are hidden. |
| 8 - Team productivity | M22-M25 rules are shown in the page. Cancelled tasks are excluded from completion and velocity; blocked tasks and reopen events remain visible. In SP-01, T01: 162 points, 4.64-day cycle time, 96.00% on-time, 90.91% completion, 2 blocked and 4 reopen events. T02: 210 points, 4.79-day cycle time, 93.65% on-time, 92.65% completion, 2 blocked and 4 reopen events. T01/T02 values were manually recalculated from clean task rows and match governed views. |
| 9 - Payroll cost | PQ-09 checks all 18 months and all 11 listed payroll/ledger/cash/receivables fields with zero mismatching months. Four payroll rows are excluded from clean totals: two duplicate employee/run keys and two unmatched employee references. The app lists source row and reason without showing employee IDs or amounts. Role-level displays require at least five employees and show aggregates only. |
| 10 - Budget and targets | Variance is actual payroll cost minus budget; positive is overspend. September 2026 D01 is +INR 214,404.24 (+1.03%, amber); D03 is +INR 30,889.62 (+0.48%, amber); D02 is -INR 42,581.21 (underspend). The two largest overspend recommendations are to review open roles and overtime before next month close. Budget colors use the page's stated 0%/5% bands; KPI status follows each target's higher/lower direction and status is color-coded. |

## Issues and fixes

- Four invalid payroll records would distort totals; the clean layer excludes them with row-level reasons while retaining the raw source. Reconciliation now matches the reference for every month.
- A low attendance month can overlap holidays and leave. The page now marks public holidays and Friday/Monday anchors, adds approved leave context, and avoids treating overlap as proof of cause.
- Velocity alone can misstate delivery health. The team page puts velocity beside cycle time, on-time delivery, blocked and reopened work and includes a T01/T02 comparison.

## Run the checks

```powershell
python etl.py
python -m unittest discover -s tests -v
python scripts/verify_acceptance.py
python scripts/build_phase2_report.py
```

The rendered application screenshot and the current workforce dashboard screenshot are embedded in the Phase 2 PDF. Source evidence remains in the linked task pages and this validation note.
