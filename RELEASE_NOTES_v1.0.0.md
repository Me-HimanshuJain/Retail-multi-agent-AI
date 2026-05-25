# v1.0.0 Release Notes

## Highlights

- Public release preparation for the retail multi-agent AI repository.
- Reconciled dependencies with the actual runtime and test imports.
- Added a fresh-clone validation script for repeatable release checks.
- Added release checklist, scorecard, and README release badges.

## Validation

- Fresh virtual environment install passes.
- `python -m compileall src` passes.
- `pytest -v --cov` passes with coverage above 80%.
- API health endpoint boots and responds successfully.
- Simulation runner executes and prints metrics.

## Notes

- Docker validation is part of the repository workflow, but it depends on Docker being installed on the host machine.