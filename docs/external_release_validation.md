# External release validation

Checked on 19 November 2026.

## Public dashboard

- URL: [pulseiq-workforce.streamlit.app](https://pulseiq-workforce.streamlit.app)
- The owner-browser check displayed the dark PulseIQ dashboard, the governed headline metrics and the 30 September 2026 cutoff without a repository credential.
- The release contains aggregate fictional training data. The visible persona control is a role simulation, not production authentication.
- Strict Task 17 evidence still required from the owner: one physical-phone screenshot and confirmation that an independent viewer could open the link and identify the month-end headcount of **441** without guidance.

## Public metrics API

- URL: [pulseiq-metrics-api-fezs.onrender.com](https://pulseiq-metrics-api-fezs.onrender.com)
- Render service: `pulseiq-metrics-api` from the repository Docker blueprint.
- `GET /health` returned HTTP 200 with `status=ok` and `read_only=true`.
- `GET /api/metrics` listed M01, M04, M09, M20 and M22.
- Each metric endpoint returned a governed September 2026 company result with its definition, source, cutoff `2026-09-30`, freshness and aggregate-only privacy statement.

| Metric | Checked value |
|---|---:|
| M01 headcount | 441 |
| M04 monthly attrition | 0.702576% |
| M09 employer payroll cost | INR 55,519,621.87 |
| M20 days sales outstanding | 47.9977 days |
| M22 task completion | 85.5146% |

The free Render service may take longer on the first request after an idle period. No secret value is included in this evidence.

## Personal release evidence still required

1. Capture the physical-phone dashboard screenshot and independent-viewer result described above.
2. Record the required face-and-screen walkthrough using `docs/board_demo_script.md`.
3. Upload the recording with link access enabled, place the link in the final submission if required, and submit the PDF through the programme form.
