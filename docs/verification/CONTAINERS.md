# Container verification — 2026-10-17

Executed locally on Apple Silicon macOS with Docker Desktop and an isolated
Minikube Docker-driver cluster (`flunky-check`). No existing application database
or Kubernetes deployment was modified.

- `python -m pytest --cov=cli --cov=backend --cov-fail-under=90`: **645 passed**, **92.92% coverage**. One existing Starlette/httpx deprecation warning remains.
- Ruff lint and format checks, mypy and `git diff --check`: passed.
- `uv build`: source distribution and Python wheel built.
- Linux arm64 and amd64 container builds: passed using locked, hash-checked dependencies.
- amd64 container CLI `--version`: passed under Docker emulation; this is not native Intel/Windows host verification.
- Compose: PostgreSQL readiness, automatic migrations, API health and deployed API smoke passed.
- Account, session and task persisted across `compose down` / `up`, including repeated migrations.
- Containerized CLI password login, task add/list and logout: passed with persistent CLI volume.
- Minikube: PVC provisioned, PostgreSQL and API became ready, hardened API filesystem worked, and deployed API smoke passed after rollout.
- `scripts/smoke_api.py` checks readiness, registration, login, tagged task queries, completion and deletion; its temporary account is deleted afterwards.
- `scripts/verify_live.py`: local SQLite API / real CLI workflow and server-side token revocation passed.
- Secret generation command was exercised through the documented Docker bind mount and preserves an existing credential file.

Regression coverage includes bounded limiter memory under 10,001 recent
identities, PostgreSQL passwords with reserved URL characters, migration startup
failure behavior and preservation of generated credentials. Backoff on a
long-running host was also checked; the original backoff behavior was correct.

GitHub Actions now contains Compose and Kubernetes runtime smoke jobs, but those
hosted jobs have not been run as part of this local verification. Native Windows
and Intel hardware, a remote registry push, public ingress/TLS, mail delivery and
multi-replica shared rate limiting were not verified. Deployment defaults retain
one API process/replica and disable email delivery; see ../CONTAINERS.md.
