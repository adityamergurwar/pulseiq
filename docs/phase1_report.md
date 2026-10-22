# PulseIQ Phase 1 report

**Name:** Aditya Mergurwar
**Track:** Data Analytics · Aura Workforce by Growmar  
**Phase:** 1 · Foundation  
**Repository:** [Private `pulseiq` repository](https://github.com/adityamergurwar/pulseiq); code push pending
**Git tag:** Local `phase-1` tag marks the final release commit; pushing the branch and tag is pending.

## Five-task evidence

| Task | Status | Evidence |
|---|---|---|
| 1 · ETL and contracts | Complete locally | `python etl.py`; 29 source files; rows in = passed + quarantined for every source table; 297 dictionary schema checks over 23 operational tables; specialized rules for four feeds; see `docs/validation_results.md`. |
| 2 · Star-schema warehouse | Complete locally | `docs/star_schema.md`; 0 declared warehouse orphans; history joins through `employee_key`. |
| 3 · Quality gatekeeper | Complete locally | 14 checks run on every load; injection test for every check; all 11 issue categories from the validation key are detected and recorded. Raw findings remain visible for owner review. |
| 4 · Governed metric layer | Complete locally | 28 views return rows; metric catalog includes formula, source, grain, owner, caveat and minimum group size; hand calculations below match. |
| 5 · Workforce dashboard | Complete locally | `app.py`; five CEO questions answered with month and department filters, cards, trend, mix charts and numeric chart insights. The screenshot exception was fixed and is covered by a regression test. |

## Proof it works

The local test suite has 7 passing tests. Two consecutive ETL runs produced the same business snapshot: 29 source tables, 62,770 input rows, 62,742 passing rows, 28 quarantined rows, zero declared orphans and 28 metric views. The acceptance script independently checks all 28 metric views, five hand calculations, the 18-month PQ-09 answer key and the privacy-safe PQ-13 reference. The maximum clean payroll-to-ledger difference is INR 0.00000004, inside the INR 0.01 tolerance. All 18 declared one-person D00 department-months are suppressed from the PQ-13 output.

The ETL preserves source rows. The current training data contains known issues, so raw DQ results include critical failures and warnings. The corresponding corrections and quarantine decisions are shown in `docs/data_quality.md` and `docs/validation_results.md`; the data-quality page continues to show `REVIEW REQUIRED` until an owner reviews those findings.

## Five hand calculations

| Metric | Independent calculation | Governed result | Check |
|---|---:|---:|---|
| M01 headcount, D01 | 167 | 167 | Pass |
| M07 gross pay, D01 | INR 20,720,901.38 | INR 20,720,901.38 | Pass |
| M13 attendance rate, D01 | 96.1784% | 96.1784% | Pass |
| M17 ledger net profit | INR 14,985,979.13 | INR 14,985,979.13 | Pass |
| M20 event-based DSO | 47.9977 days | 47.9977 days | Pass |

## Dashboard questions

1. How many people are in the workforce now, and how has headcount changed over time?
2. Which departments account for the largest share of headcount?
3. How many people joined and left in the selected month?
4. Which location tier contains the most employees?
5. Which work mode is most common?

## Learning summary draft

The implementation shows how preserving source rows and quarantining invalid rows keeps row counts explainable. Employee history must join by the version key for a time-correct department result. A governed metric view keeps dashboards and the API on one formula. A suppressed group can be analytically correct and still be unsafe to display. The report and demo owner should confirm this summary reflects their own learning before external submission.

## Problems and fixes

- The workforce page failed because its prior-month SQL contained three placeholders but passed two values. The query now binds the department twice and the selected period once; a regression test covers company and department scopes.
- The supplied data includes planted payroll, attendance, task, invoice, leave, expense, attrition-risk and SCD issues. They remain visible in raw audit results, while documented clean-layer logic corrects or excludes appropriate rows.
- Forecast actuals do not overlap the supplied forecast horizon. M28 correctly returns no forecast-error value rather than presenting a misleading accuracy score.

## Next phase and submission

The local project implements all 20 playbook modules, with hosted work and owner actions tracked in the acceptance matrix. The private repository push and phase tag are pending. Public deployment, hosted refresh, `fobesitech` collaborator, live phone test, recorded five-minute demo and programme upload still need to be completed before submission.
