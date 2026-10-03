"""Validated, additive blueprints. Rendering never executes template code or hooks."""

import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Literal

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, ConfigDict, Field

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
STACKS = (
    "python",
    "cli",
    "fastapi",
    "ds",
    "nextjs",
    "mern",
    "nestjs",
    "electron",
    "react-native",
    "flutter",
)
TYPES = ("app", "fullstack", "monorepo", "library", "cli")
ADDONS = ("docker", "ci", "database", "auth", "linting", "docs-site", "testing", "monorepo")


class ScaffoldError(ValueError):
    pass


class FileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    src: str
    dest: str


class Hook(BaseModel):
    model_config = ConfigDict(extra="forbid")
    argv: list[str] = Field(min_length=1)
    timeout: int = Field(default=300, ge=1, le=900)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str
    description: str
    files: list[FileSpec]
    post_create: list[Hook] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise ScaffoldError(f"Unsafe template path: {value}")
    for part in path.parts:
        if (
            len(part) > 100
            or part.endswith((".", " "))
            or re.search(r'[<>:"|?*\x00-\x1f]', part)
            or part.split(".")[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10)),
            }
        ):
            raise ScaffoldError(f"Path is not portable: {value}")
    return value


def validate_name(name: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,63}", name):
        raise ScaffoldError(
            "Use 1–63 letters, numbers, underscores or hyphens for the project name."
        )
    safe_path(name)
    return name


def load_manifest(folder: Path) -> Manifest:
    if not folder.is_dir():
        raise ScaffoldError(f"Template '{folder.name}' not found.")
    try:
        return Manifest.model_validate_json((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ScaffoldError(f"Manifest for '{folder.name}' is invalid: {exc}") from exc


def render_layer(folder: Path, context: dict[str, str]) -> dict[str, str]:
    manifest = load_manifest(folder)
    env = SandboxedEnvironment(undefined=StrictUndefined, keep_trailing_newline=True)
    result: dict[str, str] = {}
    for spec in manifest.files:
        source = folder / safe_path(spec.src)
        if source.is_symlink() or not source.resolve().is_relative_to(folder.resolve()):
            raise ScaffoldError("Template sources cannot escape their directory.")
        dest = safe_path(env.from_string(spec.dest).render(context))
        if dest in result:
            raise ScaffoldError(f"Duplicate template destination: {dest}")
        result[dest] = env.from_string(source.read_text(encoding="utf-8")).render(context)
    return result


def plan_project(
    stack: str,
    name: str,
    project_type: str = "app",
    addons: tuple[str, ...] = (),
    license_name: str = "MIT",
) -> tuple[dict[str, str], list[tuple[str, Hook]], list[str]]:
    validate_name(name)
    if project_type == "single-app":
        project_type = "app"
    if project_type not in TYPES or set(addons) - set(ADDONS):
        raise ScaffoldError("Unknown project type or add-on. See `flunky init --help`.")
    from cli.config import CONFIG_DIR

    folder = (
        TEMPLATES_DIR / stack if stack in STACKS else CONFIG_DIR / "templates" / safe_path(stack)
    )
    manifest = load_manifest(folder)
    layers = [(folder, "")]
    if project_type == "fullstack":
        backend = stack in {"python", "cli", "fastapi", "ds", "nestjs"}
        layers = [
            (folder, "backend" if backend else "frontend"),
            (
                TEMPLATES_DIR / ("nextjs" if backend else "fastapi"),
                "frontend" if backend else "backend",
            ),
        ]
    elif project_type == "monorepo" or "monorepo" in addons:
        layers = [(folder, "apps/main")]
    elif project_type == "cli" and stack != "cli":
        layers = [(TEMPLATES_DIR / "cli", ""), (folder, "apps/main")]
    elif project_type == "library":
        layers = [(folder, f"packages/{name}")]
    context = {
        "project_name": name,
        "package_name": "project_" + name.lower().replace("-", "_"),
        "stack": stack,
        "project_type": project_type,
        "blueprint_version": manifest.version,
        "layout": "\n".join(f"- {prefix or '.'}: {f.name}" for f, prefix in layers),
        "next_steps": "",
        "validation": "python scripts/check.py",
        "ci_steps": "",
    }
    ci: list[str] = []
    files: dict[str, str] = {}
    hooks: list[tuple[str, Hook]] = []
    steps: list[str] = []
    for source, prefix in layers:
        current = load_manifest(source)
        cwd = prefix or "."
        if source.name in {"python", "cli", "fastapi", "ds"}:
            ci.extend(
                [
                    "      - uses: astral-sh/setup-uv@v6",
                    f"      - run: uv sync --extra dev && uv run pytest && uv run ruff check .\n        working-directory: {cwd}",
                ]
            )
        elif source.name == "flutter":
            ci.extend(
                [
                    "      - uses: subosito/flutter-action@v2\n        with:\n          channel: stable",
                    f"      - run: flutter pub get && flutter analyze && flutter test\n        working-directory: {cwd}",
                ]
            )
        elif source.name in STACKS:
            ci.extend(
                [
                    "      - uses: actions/setup-node@v4\n        with:\n          node-version: '22'",
                    f"      - run: npm install && npm test && npm run lint && npm run build\n        working-directory: {cwd}",
                ]
            )
        steps.extend(
            f"{('cd ' + prefix + ' && ') if prefix else ''}{s}" for s in current.next_steps
        )
        hooks.extend((prefix, hook) for hook in current.post_create)
        for path, content in render_layer(source, context).items():
            files[f"{prefix}/{path}" if prefix else path] = content
    context["next_steps"] = "\n".join(steps)
    context["ci_steps"] = "\n".join(ci)
    base = render_layer(TEMPLATES_DIR / "_base", context)
    if "README.md" in files:
        files["docs/stack.md"] = files.pop("README.md")
    base[".gitignore"] += files.pop(".gitignore", "")
    if ".env.example" in files:
        base[".env.example"] += "\n" + files.pop(".env.example")
    files.update(base)
    if license_name == "MIT":
        files["LICENSE"] = (
            "MIT License\n\nCopyright (c) the project contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
        )
    elif license_name == "UNLICENSED":
        files["LICENSE"] = (
            "All rights reserved. No permission to use, copy, modify, or distribute is granted.\n"
        )
    else:
        raise ScaffoldError("Supported licenses: MIT, UNLICENSED.")
    if project_type == "monorepo" or "monorepo" in addons:
        files["packages/shared/README.md"] = (
            "# Shared packages\nPlace reusable domain code here; keep application entry points in apps/.\n"
        )
    if "database" in addons or "docker" in addons:
        files["compose.yaml"] = (
            "services:\n  database:\n    image: postgres:16-alpine\n    environment:\n      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}\n    volumes:\n      - postgres:/var/lib/postgresql/data\nvolumes:\n  postgres:\n"
        )
    if "auth" in addons:
        files["docs/auth.md"] = (
            "# Authentication integration\nAuthentication is not enabled by this blueprint. Choose an identity provider, verify tokens server-side, enforce authorization on every resource, and add ownership and session-revocation tests before deployment. Never implement password storage in client code.\n"
        )
    if "docs-site" in addons:
        files["mkdocs.yml"] = f"site_name: {name}\ntheme:\n  name: material\n"
        files["docs/requirements.txt"] = "mkdocs-material>=9,<10\n"
    files[".flunky.json"] = (
        json.dumps(
            {
                "schema_version": 1,
                "blueprint_version": manifest.version,
                "stack": stack,
                "type": project_type,
                "addons": addons,
                "license": license_name,
            },
            indent=2,
        )
        + "\n"
    )
    return files, hooks, steps


def write_files(target: Path, files: dict[str, str], *, allow_existing: bool = False) -> list[str]:
    if target.is_symlink():
        raise ScaffoldError("Target cannot be a symbolic link.")
    target = target.resolve()
    if target.exists() and any(target.iterdir()) and not allow_existing:
        raise ScaffoldError("Target is not empty. Confirm with --yes, or choose another directory.")
    for path in files:
        dest = target / safe_path(path)
        if len(str(dest.absolute())) > 240:
            raise ScaffoldError(f"Path exceeds the portable 240-character limit: {dest}")
        if any(p.is_symlink() for p in (dest, *dest.parents)):
            raise ScaffoldError(f"Refusing symbolic link destination: {dest}")
    written = []
    for path, content in files.items():
        dest = target / path
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        written.append(path)
    return written


def run_hook(target: Path, hook: Hook) -> None:
    try:
        subprocess.run(
            hook.argv, cwd=target, check=True, timeout=hook.timeout, capture_output=True, text=True
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ScaffoldError(
            f"Post-create command {hook.argv[0]!r} failed; generated files are preserved. Run it manually to inspect the error: {exc}"
        ) from exc


def scaffold_project(project_type: str, project_name: str, target_dir: str | None = None) -> str:
    files, _, _ = plan_project(project_type, project_name)
    target = Path(target_dir or project_name).absolute()
    write_files(target, files)
    return str(target)
