"""Portable source/metadata sanity checks, without installing project dependencies."""
import ast
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in ("README.md", "LICENSE", ".gitignore", "SECURITY.md", "CONTRIBUTING.md"):
    if not (root / name).is_file():
        raise SystemExit(f"Missing required file: {name}")
for path in root.rglob("*"):
    if any(part in {".git", ".venv", "venv", "node_modules", ".next", ".dart_tool"} for part in path.parts):
        continue
    if path.suffix == ".py":
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    elif path.suffix in {".json", ".ipynb"}:
        json.loads(path.read_text(encoding="utf-8"))
print("Source and metadata checks passed")
