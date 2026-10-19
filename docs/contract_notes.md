# Contract notes

The contract file contains row-level promises for four fact feeds. These notes summarize three of them; enforcement is in `etl.py`.

## `fact_task` · task board

- Required identifiers: `task_id` matches `TASK-nnnnn`; `team_id`, `sprint_id`, and `assignee_employee_id` must be present.
- `task_type` is Feature, Bug, Chore, or Spike; priority is P1–P4; story points are 1, 2, 3, 5, 8, or 13.
- Created and due dates are required. Start and completed dates may be empty, but start may be blank only for To Do; completed date is required when status is Done and cannot precede start. Due date is required and should match the sprint end date.
- Status must be Done, In Progress, Blocked, To Do, or Cancelled; reopened count must be nonnegative.

## `fact_forecast` · AI forecast

- Forecast ID matches `FC-nnnn`; metric is headcount_end or attrition_rate_monthly_pct.
- Department scope is a department ID or ALL; forecast month is a date; point forecast is nonnegative.
- The 80% lower bound must be at or below the point forecast and the upper bound at or above it.
- Method, training cutoff, and model version are required provenance fields.

## `fact_attrition_risk` · AI attrition risk

- Prediction ID matches `AR-nnnn`; employee and department keys and as-of date are required.
- Risk score is between 0 and 1; risk band is Low, Medium, or High.
- Up to three plain-language reasons can be blank; model version is required.
- Risk scores are group-level signals, not determinations about individuals. The dashboard suppresses groups under five.

## Unexpected columns

Keep new source columns in `raw` and `clean`, then warn and review before exposing them in metrics. That preserves evidence while avoiding silent loss and gives the team time to decide whether the contract and downstream logic must change. Missing contracted columns stop the run; violations are quarantined with a reason.
