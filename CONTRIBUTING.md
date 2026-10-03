# Contributing

Use Python 3.10–3.13 and uv. Run `uv sync --locked --extra dev --extra test`. Keep changes focused and use conventional commits (`fix:`, `feat:`, `docs:`, `chore:`).

Before a PR, run ruff lint/format on cli, backend, tests and scripts; `uv run mypy`; and `uv run python -m pytest --cov --cov-fail-under=90`. Use temporary databases/config directories; never test against another person's credentials or database. Backend schema changes need an Alembic migration with upgrade/downgrade coverage.

For command changes, regenerate `python -m scripts.generate_help` and `python -m scripts.generate_docs`. Blueprint assets are maintained by `scripts/build_template_assets.py`; run its module after editing the source. Check both generated files and ecosystem build commands. Tests must verify behavior, including errors and preservation of user data.

Run `uv run pre-commit install` for local formatting hooks. Explain the user-visible problem, change, verification and remaining limitations in your PR. Security reports belong in a private channel; see SECURITY.md.
