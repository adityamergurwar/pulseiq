# Privacy and role break tests

PulseIQ applies scope before returning explorer results. The local persona selector is a deterministic demonstration of the authorization rules; hosted production use must enable login and supply password hashes through the platform secret store.

| Role | Allowed scope | Intended metric access |
|---|---|---|
| ADMIN | Company, department and supported team drill-down | Full governed catalog |
| HR | Assigned department; supported task teams within it | Workforce, attendance, attrition, aggregate payroll and task metrics |
| MANAGER | Assigned team only | M22-M25 task delivery metrics |
| EXECUTIVE | Company level only | Non-sensitive company aggregates; no payroll detail |

## Break-test decisions

1. A manager cannot select another team or a company/department dimension. The team choice is filtered to the account's assigned `team_id`.
2. An HR user cannot change the department selector. It is fixed to the account's assigned `department_id`.
3. An executive cannot request department, team or individual salary views. Salary-detail metric IDs are removed before the selector is rendered.
4. Task groups smaller than five eligible records are suppressed. People metrics use the metric dictionary's minimum group size.
5. The one-person D00 reference group is not displayed in people or payroll aggregates. Phase 4 validation confirms 81 D00 department-month rows remain excluded.
6. A new department is not hard-coded into charts: the automated D99 fixture appears in the budget view without an application change.

Automated evidence is in `tests/test_access_control.py`, `tests/test_phase4_release.py` and `scripts/verify_phase4.py`. The tests exercise role boundaries, hosted secret loading, seeded issue dispositions, minimum-group rules and the dynamic-department path.
