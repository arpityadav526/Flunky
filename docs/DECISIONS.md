# Decisions

- M0: Treat the supplied status.txt as STATUS_REPORT.txt and archive it unchanged for provenance.
- M0: Preserve the local flunky.db, existing venv, editor settings, and user-generated my-ml-project; untrack and ignore local data.
- M0: Preserve the launch post as a historical draft, not current product documentation.
- M1: Keep the legacy bcrypt/Jose stack until M3; pin bcrypt below 4.1 for passlib compatibility in clean installations.
- M1: Apply strict mypy to new code; retain explicit legacy overrides until each backend/CLI module is migrated.
- M1: Preserve existing API payloads and commands; use bounded connection retries only, never automatically replay potentially committed HTTP writes.
- M1: Package all template assets with hatchling and use uv locked installs in CI (https://hatch.pypa.io/dev/config/build/, https://docs.astral.sh/uv/guides/integration/github/).
