# Launch readiness

**Assessment: locally verified release candidate; not yet ready for an unrestricted public launch.** Verification date: 2026-10-03, macOS Apple M3. M0–M7 implementation and local verification are recorded in [VERIFICATION.md](VERIFICATION.md). No hosted Windows run, public PyPI upload, public tap installation, Developer ID notarization or Windows signing is claimed.

## Scorecard

Scores describe evidence and remaining work, not a certification.

| Area | Score / 10 | Evidence and limits |
|---|---:|---|
| Repository/tooling | 9 | uv lock, PEP 621 wheel/sdist, ruff lint/format and mypy passed; 48 modules checked. Legacy modules retain scoped typing exceptions. |
| Tests | 9 | 625 tests pass on local macOS Python 3.10, 3.11, 3.12 and 3.13; 92.50% combined CLI/backend coverage on 3.13; three snapshots pass. |
| CLI behavior | 9 | 109 installed-wheel subprocess invocations cover every registered command path, both login modes, task lifecycle, all scaffold stacks, configuration, project shortcuts, completion and offline replay. Real PTY TUI launch/q exit passes; headless tests cover search, completion and undo. |
| Startup | 10 | Apple M3 warm help median 16.5ms; hyperfine mean 14.4ms over 20 runs after five warmups, below the 150ms budget. Binary extraction is not included in this number. |
| Backend/data | 8 | Async SQLAlchemy, Alembic upgrade/downgrade tests, Postgres 16 real Docker API smoke, non-root two-worker image, health/readiness and ownership tests pass. Deployment/backups/load testing remain. |
| Authentication/security | 8 | Rotation/replay revocation, device flow, PATs, email/reset actions, Argon2id, lockout and logout tests pass. Runtime dependency audit reports no known vulnerabilities; first-party Flunky itself is skipped by the advisory service. Production email/shared rate limiting are not implemented. |
| Project generation | 7 | All 12,800 stack/type/add-on subsets generated and parsed; all ten stacks installed and passed their ecosystem checks where defined. Auth add-on is guidance; library layout does not implement publication semantics for every framework; native wrappers/signing remain separate. |
| Generated dependency security | 5 | Next.js/MERN/NestJS and updated Electron installation audits report zero vulnerabilities. Expo SDK 57 still reports 23 transitive advisories (7 moderate, 16 high); see retained audit. |
| Docs/distribution | 8 | README, demo GIF, generated reference, strict MkDocs build, wheel/sdist, local arm64 PyInstaller binary and runtime SBOM exist. Release/CodeQL/tap workflows are configured but have not run on hosted CI. |
| Platform compatibility | 6 | Four Python versions verified on Apple Silicon and Linux backend in Docker. Windows/Linux CLI and macOS Intel CI are configured, not executed; native terminal/keychain visual checks remain. |

## Commands actually run

- `ruff check cli backend tests scripts packaging`, `ruff format --check ...`, `mypy`: passed in a clean verification environment.
- `python -m pytest -q --cov --cov-report=term:skip-covered --cov-report=xml`: passed; 625 tests, 92.50% coverage. Separate clean Python 3.10/3.11/3.12 runs each passed 625 tests.
- Built wheel/sdist, installed the wheel into a new venv, then `python -m scripts.verify_cli_surface --cli <fresh-venv>/bin/flunky`: 109 passed. [Exact invocation log](verification/cli-surface.txt).
- `python -m scripts.verify_blueprints`: 12,800 generated combinations passed. Electron/Expo subsets were regenerated after dependency updates. Each stack's generated test/lint/build entry points were also exercised independently.
- Python/CLI/FastAPI/data-science: uv sync, pytest, ruff; Next.js/MERN/NestJS/Electron/Expo: npm install, npm test, npm run lint/build; MERN typecheck; Flutter pub get, analyze and widget tests: passed. These are source/build checks, not mobile/device UI or store certification.
- `docker build -t flunky:final .` and `python -m scripts.verify_postgres`: passed with PostgreSQL 16, migrations, readiness, registration/login, tags/priority filtering, soft delete/restore and logout invalidation. Test containers/network/anonymous DB volume were removed. Final rebuilt arm64 image: 110,251,405 bytes; runtime user `flunky`.
- `python scripts/check_startup.py`, hyperfine and import-time tracing: passed; raw timings in [performance](performance/startup-final.json).
- `pip-audit --path <fresh-venv>/lib/python3.13/site-packages`: [no known runtime dependency vulnerabilities](verification/python-audit.txt). SBOM generated against the clean installed environment as `dist/sbom.cdx.json`.
- `vulture cli backend --min-confidence 80`: four findings, reviewed as framework/protocol parameters (two Pydantic `cls` parameters, provider `prompt`, Typer's global JSON parameter). [Raw findings](verification/vulture.txt); the scan is not falsely reported as zero findings.
- `python -m scripts.generate_docs`, `mkdocs build --strict`, PyInstaller arm64 build, binary version/fullstack dry run, and ad-hoc codesign verification: passed. No external publisher signing or notarization performed.

## Security checks and known limitations

- Password hashes use Argon2id; legacy bcrypt is upgraded after successful verification. Access/refresh tokens are revocable; refresh reuse revokes the token family. Tests cover expiry, purpose/audience/issuer and ownership isolation.
- Request errors exclude submitted secret values; CLI errors do not emit normal-operation tracebacks. User credentials and local DB were not used for verification.
- Template hooks use checked argument arrays and timeouts. Custom hook installation requires explicit trust. Generation rejects unsafe paths and preserves existing files. Completion writes dedicated files without changing startup profiles.
- **Expo dependency blocker:** SDK 57.0.26 / RN 0.86.3 still resolves vulnerable transitive dependencies. Registry queries found no newer published braces or node-forge patch at verification time. Do not treat the mobile template as security-cleared; reassess upstream updates or replace affected tooling before release. [Full audit](verification/expo-audit.json). [Electron clean audit](verification/electron-audit.json).
- Production email delivery and distributed rate limiting need real adapters. The development mailbox and process-local limiter are unsuitable as a complete multi-worker production solution.
- Offline sync is ordered but does not yet provide a cross-process synchronization lock or server-side edit conflict resolution. Run one sync process per account and review conflicting multi-device edits.
- The auth blueprint add-on documents integration only. Native mobile platform wrappers, desktop installers/signing and fully publishable framework-specific library packages are not completed by the generic layout option.
- An upstream Starlette TestClient/httpx deprecation warning remains. It did not fail tests.
- The original development venv had incomplete package metadata; final tests/audits used separate clean environments. This is an environment observation, not a runtime workaround shipped in the product.

## Maintainer actions before public launch

1. Push the commits and obtain green hosted macOS/Windows/Linux CI; run the installed CLI and terminal/keychain checklist on Windows and Intel macOS. No Windows runner was available in this local execution.
2. Resolve or explicitly defer the Expo security blocker and the incomplete generator features above. Implement production email delivery and shared rate limiting before a multi-worker public API deployment.
3. Confirm PyPI name ownership, create the Trusted Publisher for `release.yml` / `pypi`, protect the environment, and perform a real public install verification after publishing. `pip install flunky` is not yet verified as this release.
4. Configure Apple Developer ID/notarization and Windows signing credentials. Sign before generating final hashes/manifests; test Gatekeeper/SmartScreen on clean machines.
5. Create/configure the Homebrew tap and scoped update token. Validate the generated Homebrew/Scoop/winget manifests with native tools and submit to the intended repositories. No fake binary hashes are committed.
6. Choose API/docs hosting and domains, configure HTTPS/secrets/Postgres/backups/mail/Sentry retention, enable private security reporting, and verify recovery/load behavior.

See [release procedure](RELEASING.md) for account/workflow setup. No billing or AI agent was implemented; the hidden `ai` group exposes only a future provider contract.
