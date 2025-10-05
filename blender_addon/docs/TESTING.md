# Testing & Linting

## Setup

Install dev dependencies (creates an isolated environment as you prefer):

```bash
pip install -e .[dev]
```

## Run Tests

```bash
pytest  # now enforces 90%+ coverage (pure-Python scope)
```

## Lint (Ruff)

```bash
ruff check .          # report
ruff check --fix .    # auto-fix (preferred in CI/pre-commit)
```

## Pre-commit Hooks

Install pre-commit to auto-run Ruff + tests on commits:

```bash
pip install pre-commit
pre-commit install
```

(First run may be slower while environments initialize.)

## Notes

- Tests avoid Blender dependency by only exercising pure-Python modules (e.g. `data_loader`). Blender-dependent code is guarded so import smoke tests still pass.
- Add more fixtures in `tests/fixtures/` for broader schema coverage.
- For Blender integration tests, consider a separate suite using a headless Blender invocation.
