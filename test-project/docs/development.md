# Development

uv sync --extra dev
uv run pytest
uv run ruff check .

## Validation

python scripts/check.py

Use a supported runtime, install dependencies locally, commit the resulting lockfile, then reproduce builds from that lockfile. The template creates no cloud resources or accounts. For native mobile builds, install the platform SDKs and signing tools separately.
