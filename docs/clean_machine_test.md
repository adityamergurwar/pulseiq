# Clean-environment release test

## Scope

The release candidate pins every direct Python dependency and targets Python 3.11 in Docker and GitHub Actions. On 18 November 2026, the test created an empty virtual environment, installed only `requirements.txt`, rebuilt the warehouse, ran the automated checks and built the September PDF and Excel packs.

Result: 28 automated tests passed, the Phase 3 verifier passed 12/12 groups, and the Phase 4 verifier passed 11/11 groups. The isolated warehouse and report artifacts were written under `.artifact_build/` and did not reuse the project virtual environment.

## Commands

```powershell
python -m venv .artifact_build\phase4_clean_venv
.artifact_build\phase4_clean_venv\Scripts\python.exe -m pip install -r requirements.txt
.artifact_build\phase4_clean_venv\Scripts\python.exe etl.py
.artifact_build\phase4_clean_venv\Scripts\python.exe -m unittest discover -s tests -v
.artifact_build\phase4_clean_venv\Scripts\python.exe scripts\verify_acceptance.py
.artifact_build\phase4_clean_venv\Scripts\python.exe scripts\verify_phase3.py
.artifact_build\phase4_clean_venv\Scripts\python.exe scripts\verify_phase4.py
```

The local machine currently provides Python 3.13. The same exact dependencies run under Python 3.11 in `Dockerfile`, `Dockerfile.api` and `.github/workflows/monthly-refresh.yml`. The Docker daemon was unavailable during this release pass, so the new isolated virtual-environment run is the current clean-folder evidence; the previous Python 3.11 container initialization is recorded in `docs/validation_results.md`.

## New-department test

`tests/test_phase4_release.py` injects a fictional D99 budget row into the monthly chart builder. The chart discovers the department from data and renders it without a fixed department list. The dashboard selectors also read departments from `clean.dim_department`, so a valid new department appears after the next ETL refresh. Invalid or very small people groups remain governed by the catalog privacy floor.

