# Final Submission Checklist

- [x] Dashboard is deployed at <https://pulseiq-workforce.streamlit.app> and loaded in the owner's browser on 2026-10-22. **Still needed:** open it from a phone and ask another viewer to test it.
- [ ] Production authentication is enabled in Streamlit Secrets and the login screen is confirmed. The latest supplied screenshot still showed the demo persona selector.
- [ ] Confirm restricted ADMIN/HR salary access, scoped HR/manager access, company-only executive view and grouped risk results on the hosted app.
- [x] Monthly refresh/report workflow is configured in `.github/workflows/monthly-refresh.yml`.
- [ ] Confirm the first GitHub Actions workflow run passes. The workflow can rebuild the supplied data snapshot; a changing source feed is still needed to advance the 2026-09-30 cutoff.
- [x] Repository has setup steps, project architecture and fictional-data notice.
- [x] Local core outcomes for PQ-01–PQ-16 and PQ-18–PQ-19 are documented in `docs/task_acceptance_matrix.md`.
- [x] Answer-key comparisons, DQ findings and clean reconciliation are in `docs/validation_results.md`.
- [x] Architecture, metric lineage and release notes are included.
- [x] Local Phase 1 report, September management PDF, nine-sheet Excel snapshot and nine-slide board deck are in the output folders listed in `README.md`.
- [ ] Record the five-minute live demo from `docs/board_demo_script.md` after phone and viewer checks.
- [x] No production password or secret value is stored in source files; production configuration uses host secrets.
- [x] Push the private repository and annotated `phase-1` tag; record the repository URL in `docs/phase1_report.md`.
- [ ] Add `fobesitech` as a collaborator and confirm the invite is accepted or pending in GitHub.
- [ ] Confirm the learning summary in the owner's own words.
- [ ] Upload the named Phase 1 PDF and final required files to the programme site.
