# Repository-wide test coverage audit

## Goal

Audit the complete Python application and add meaningful missing tests for core
logic, failure handling, boundary conditions, and regression-prone behavior.

## Scope

- Production Python code under `src/`, plus route/wiring logic in `app.py`.
- Existing unit, integration, UI, and offline end-to-end tests under `tests/`.
- Offline, deterministic coverage is the primary acceptance signal.
- Online APIs, live LLM calls, and browser-dependent Playwright flows are
  inspected but excluded from the mandatory proof run unless locally available.

## Work order

1. Run the existing offline suite with branch coverage and preserve the baseline.
2. Map uncovered files and branches to existing tests and rank gaps by behavior risk.
3. Add focused tests for untested public behavior, validation, errors, and boundaries.
4. Run targeted tests while iterating, then rerun the complete offline proof command.
5. Review the full diff and publish a concise coverage delta and residual-risk report.

## Bounds

- Prefer tests-only changes. Modify production code only when a test exposes a real
  defect that must be fixed for the specified behavior, and report such changes.
- Do not make network calls or require user credentials.
- Do not inflate coverage with assertions that only execute code without validating
  observable behavior.
- Do not commit or push the coverage changes without final human diff sign-off.

## Proof command

```powershell
python -m pytest -m "not online and not benchmark and not e2e and not playwright" --cov=src --cov=app --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
```
