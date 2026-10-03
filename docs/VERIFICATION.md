# Verification log

## M0 — repository cleanup

- Ruff lint and format: passed (project-local rules).
- Mypy: passed for 19 modules using legacy follow-imports=silent and ignore-missing-imports; strict checking starts with new modules in M1.
- Full original test suite: 12 passed on macOS / Python 3.13.
- Source tree: M0_TREE.txt. Local DB and generated sample retained.

## M1 — correctness, packaging, tests and CI

- `uv sync --extra dev --extra test`: passed; uv.lock generated.
- `uv run ruff check cli backend tests`, `ruff format --check`, `uv run mypy`: passed.
- `uv run pytest --cov=cli --cov=backend -q`: 77 passed, 98.01% coverage; three output snapshots pass.
- Clean seeded venv → `python -m pip install .` → `flunky --help`, `flunky --version`: passed.
- `uv build`: wheel and sdist built; inspected wheel for all 10 manifests and 24 template assets.
- Live uvicorn on an isolated temporary DB: registration, login, real CLI create/list/complete/show/delete, and failed repeated delete passed.
- Added 12-cell macOS/Windows/Linux × Python 3.10–3.13 CI matrix and Docker build job; hosted jobs have NOT been run from this workspace.
- Template generation tests mock legacy post-create installers; ecosystem installs are deferred to M5.
- One upstream Starlette TestClient deprecation warning remains with the latest resolver result.
