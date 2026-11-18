# Independent final challenge: overdue receivables share

Branch: `codex/final-challenge-overdue-share`

## Decision and business value

The receivables page showed open value and days sales outstanding, but it did not provide one governed ratio for the immediate collection risk. M29 adds **overdue receivables share**: overdue open balance divided by total open balance at each month end. A lower value is better. It helps a finance leader distinguish a large but not-yet-due book from an aged collection problem.

## Build path

1. Invoice and payment rows are read from `clean.fact_invoice` and `clean.fact_invoice_payment`.
2. Payments received by each month end are subtracted from invoice totals.
3. Positive remaining balances are classified as overdue when `due_date < period`.
4. `metrics.m29_overdue_receivables_share` divides overdue balance by total open balance and multiplies by 100.
5. The catalog makes M29 available to ADMIN and EXECUTIVE at company level in the KPI explorer.

No employee or client row is displayed. The metric is a company aggregate, and the view returns no client identifier. The regression test independently calculates the ratio from the dashboard ageing view and matches it to eight decimal places.
