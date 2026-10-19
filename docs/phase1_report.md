# PulseIQ Phase 1 report

**Name:** [Your name]  
**Track:** Data Analytics · Aura Workforce by Growmar  
**Phase:** 1 · Foundation  
**Repository:** [Add your private GitHub URL]  
**Git tag:** `phase-1` (create and push after final review)

## Task evidence

| Task | Status | Evidence |
|---|---|---|
| 1 · ETL and contracts | Built; runtime validation pending | Add count-summary screenshot; attach quarantine summary |
| 2 · Star-schema warehouse | Built; reconciliation pending | [Star schema](star_schema.md); add orphan-check output |
| 3 · Quality gatekeeper | Built; planted-issue comparison pending | Add `audit.dq_results` output and planted-issue comparison |
| 4 · Governed metrics | Built; query and hand-checks pending | Add metric catalog output and five hand calculations |
| 5 · Workforce dashboard | Built; runtime review pending | Add dashboard screenshot and five CEO questions |

### CEO questions for the dashboard

1. How many people are in the workforce now, and how has headcount changed over time?
2. Which departments account for the largest share of headcount?
3. How many people joined and left in the selected month?
4. Which location tier contains the most employees?
5. Which work mode is most common?

## Proof it works

Run `python etl.py` and paste the summary and quality output here after dependencies are installed. Reconcile each table as rows in = passed + quarantined. Compare the DQ findings with the validation vault only after recording your own results.

## What I learned

[Write 3–5 lines in your own words. Explain one thing you can now trace from source row to dashboard.] 

## Problems and fixes

[Record issues you encountered and how you resolved them.] 

## Next phase

[Describe your plan for Phase 2.] 

## Submission checklist

- [ ] Add screenshots and completed reflections.
- [ ] Confirm the private repository URL opens; add `fobesitech` as collaborator if required by the programme.
- [ ] Create and push `phase-1` tag.
- [ ] Export this completed report to `DataAnalytics_YourName_Phase1_Report.pdf` and submit it.
