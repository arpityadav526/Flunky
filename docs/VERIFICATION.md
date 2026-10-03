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

## M2 — async backend and production infrastructure

- Ruff lint/format and mypy (29 modules, strict for new backend modules): passed.
- Full suite: 82 passed, 92.58% combined coverage, three CLI snapshots passed.
- Migration test: 0001 legacy data → head → downgrade → upgrade → base → head passed without losing the legacy task.
- `docker build -t flunky:m2 .`: passed on arm64. Image inspect reports 104,965,602 bytes and user flunky.
- Live isolated Docker network: PostgreSQL 16 + Alembic + two-worker Gunicorn API; readiness, registration/login, SQL JSON tag/priority filter, soft delete and restore passed. Temporary containers, network and anonymous DB volume removed after verification.
- Local user database was not migrated or modified; upgrade procedure is documented in BACKEND.md.

## M3 — authentication hardening

- Ruff lint/format and mypy: passed (33 modules, strict for migrated auth/config).
- Full suite: 94 passed, 96.33% coverage; three snapshots passed.
- Security tests: Argon2id + bcrypt upgrade, refresh rotation/replay family revocation, access expiry/wrong audience/issuer/purpose, logout/everywhere, one-use verification/reset, password change/account deletion, PAT creation/revocation, brute-force lockout, device pending/slow-down/approval/consumption, keychain and 0600 fallback, automatic CLI refresh.
- `uv run python scripts/verify_live.py`: passed against a real isolated migrated SQLite/uvicorn server with real password-stdin CLI login, task commands and logout; old access and refresh tokens both rejected afterwards.
- `uv run pip-audit --skip-editable`: no known vulnerabilities after upgrading pytest/syrupy.
- Development mail and keychain adapters tested without sending external email or touching the user's real credentials. Production mail/shared rate-limit adapters remain deployment prerequisites.

## M4 — CLI UX, offline mode and terminal behavior

- Ruff lint/format, strict mypy for new CLI modules: passed (44 modules).
- Expanded suite: 119 tests, including quick commands, flags before/after commands, typed responses, profiles, keychain fallback, offline ordering/ID mapping/undo, idempotent server creation and Textual keyboard/search behavior.
- Full-suite coverage: 92.66% before the packaging-only dependency correction; final run recorded below.
- Installed source build in `.install-check`: hyperfine 20 runs after 5 warmups averaged 15.4ms for `flunky --help` on Apple M3; subsequent startup check median 16.1ms (150ms target). Raw evidence in docs/performance/.
- `python -X importtime`: captured for the lightweight launcher.
- Live API/real CLI regression smoke passed for password-stdin login, task CRUD and server-side logout.
- VHS recorded docs/demos/cli.gif in a real zsh PTY. Inspected a rendered frame; it displays successful installed-CLI help. Recording exposed and fixed a missing packaging dependency.
- Root help is generated, not manually duplicated. The installed-wheel surface will be rechecked in M7.
- Final M4 run: 119 passed, 92.66% coverage, all snapshots passed.

## M5 — layered project blueprints

- Ruff lint/format and mypy passed (47 modules).
- Full suite: 623 passed, 92.44% coverage, three snapshots passed; includes 500 stack/layout/add-on combinations and path/symlink/overwrite/hook-trust regression tests.
- Built wheel and sdist; reinstalled package and ran the documented fullstack init dry run through the installed CLI.
- Generated all ten standalone stacks into isolated /tmp directories. Python, CLI, FastAPI and data-science projects passed uv installation, pytest and ruff. Next.js, MERN, NestJS, Electron and Expo passed npm installation, tests, lint and build; MERN also passed typecheck. Flutter passed pub get, analyze and widget tests.
- This verifies build/test entry points, not native signing, app-store packaging, desktop visual behavior or production deployment. Generated auth is guidance only; library layouts retain the selected stack's application semantics.
- Exhaustive follow-up: all 12,800 stack × type × add-on subsets generated and parsed successfully in temporary directories.

## M6 — documentation and distribution preparation

- README rewritten to match implemented behavior; generated nested command reference and MkDocs Material strict build passed.
- Ruff lint/format and mypy passed (48 modules); full suite: 623 passed, 92.45% coverage, three snapshots passed.
- PyInstaller built a 28,799,008-byte arm64 executable locally. Its version and fullstack dry-run commands passed; codesign verification passed for its ad-hoc signature, not a Developer ID signature or notarization.
- Release-please, OIDC publishing, binary matrix, checksum-derived Homebrew/Scoop/winget artifacts, optional tap update, Dependabot and CodeQL are configured. Hosted execution and account setup remain unverified.
