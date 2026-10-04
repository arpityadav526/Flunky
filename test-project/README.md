# test-project

python · app · generated with Flunky blueprint 1.0.0

## Start

uv sync --extra dev
uv run pytest
uv run ruff check .

## Layout

- .: python

Use `python scripts/check.py` for a portable structure/content smoke check. See docs/development.md for setup, testing and deployment. Dependency installation and external tools only run when requested. Review and commit generated dependency lockfiles before shipping.
