"""Maintain bundled Jinja assets and their versioned manifests."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "cli" / "templates"


def pack(name, files, *, description="", hooks=(), next_steps=()):
    directory = ROOT / name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    specs = []
    for index, (dest, content) in enumerate(files.items()):
        source = f"{index:02}.j2"
        (directory / source).write_text(content.rstrip() + "\n", encoding="utf-8")
        specs.append({"src": source, "dest": dest})
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "1.0.0",
                "name": name,
                "description": description,
                "files": specs,
                "post_create": list(hooks),
                "next_steps": list(next_steps),
            },
            indent=2,
        )
        + "\n"
    )


base = {
    "README.md": """# {{ project_name }}

{{ stack }} · {{ project_type }} · generated with Flunky blueprint {{ blueprint_version }}

## Start

{{ next_steps }}

## Layout

{{ layout }}

Use `python scripts/check.py` for a portable structure/content smoke check. See docs/development.md for setup, testing and deployment. Dependency installation and external tools only run when requested. Review and commit generated dependency lockfiles before shipping.
""",
    ".gitignore": """__pycache__/
*.py[cod]
.venv/
venv/
.env
.env.*
!.env.example
*.db
*.log
node_modules/
.next/
dist/
build/
coverage/
.pytest_cache/
.ruff_cache/
.DS_Store
.idea/
.vscode/
.dart_tool/
.flutter-plugins-dependencies
""",
    ".editorconfig": "root = true\n[*]\ncharset = utf-8\nend_of_line = lf\nindent_style = space\nindent_size = 2\ninsert_final_newline = true\n[*.py]\nindent_size = 4",
    ".gitattributes": "* text=auto eol=lf\n*.png binary\n*.jpg binary\n*.gif binary\n*.bat text eol=crlf",
    "CONTRIBUTING.md": """# Contributing

Open an issue with the problem and a reproducible example. Keep pull requests focused, include tests for changed behavior, run the checks in docs/development.md, and explain compatibility or migration effects. Never commit secrets or personal data.
""",
    "SECURITY.md": """# Security policy

Do not disclose credentials or exploit details in public issues. Before public release, maintainers must configure a private vulnerability reporting channel in repository settings and document supported versions here. Until that channel is configured, report only that a private security discussion is needed, without exploit details. Rotate any exposed credential immediately.
""",
    "CHANGELOG.md": "# Changelog\n\n## Unreleased\n\n- Initial project structure.",
    "CODE_OF_CONDUCT.md": """# Community code of conduct

Treat people with respect. Welcome constructive disagreement and different backgrounds. Harassment, threats, discriminatory abuse and disclosure of private information are not acceptable. Maintainers may remove harmful content and restrict participation, with decisions explained privately when possible. Establish a confidential reporting contact before opening this project to external contributors.
""",
    ".env.example": "# Copy to .env; never commit credentials.\nAPP_ENV=development\nPORT=8000",
    "Makefile": "# Portable check script is also usable directly from PowerShell.\n.PHONY: check\ncheck:\n\tpython scripts/check.py",
    "docs/index.md": "# {{ project_name }}\n\nStart with [Development](development.md) and [Architecture](architecture.md).",
    "docs/development.md": """# Development

{{ next_steps }}

## Validation

{{ validation }}

Use a supported runtime, install dependencies locally, commit the resulting lockfile, then reproduce builds from that lockfile. The template creates no cloud resources or accounts. For native mobile builds, install the platform SDKs and signing tools separately.
""",
    "docs/architecture.md": "# Architecture\n\n{{ layout }}\n\nKeep domain logic separate from transport/UI and storage. Add design decisions as short dated notes in docs/decisions.md.",
    "docs/decisions.md": "# Decisions\n\n- Created from Flunky {{ stack }} blueprint {{ blueprint_version }} as {{ project_type }}.",
    "scripts/check.py": '''"""Portable source/metadata sanity checks, without installing project dependencies."""
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
''',
    ".github/ISSUE_TEMPLATE/bug_report.yml": """name: Bug report
description: Report a reproducible problem
body:
  - type: textarea
    id: steps
    attributes:
      label: Steps and expected behavior
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Runtime, OS and version
""",
    ".github/PULL_REQUEST_TEMPLATE.md": "## Problem and change\n\nDescribe what changes for users.\n\n## Verification\n\nList commands run and results.\n\n## Compatibility\n\nDescribe migration or deployment effects.",
    ".github/dependabot.yml": """version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
""",
    ".github/workflows/ci.yml": """name: CI
on: [push, pull_request]
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python scripts/check.py
{{ ci_steps }}
""",
    ".pre-commit-config.yaml": """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-json
      - id: end-of-file-fixer
      - id: trailing-whitespace
""",
    ".devcontainer/devcontainer.json": '{"name": "{{ project_name }}", "image": "mcr.microsoft.com/devcontainers/universal:2", "postCreateCommand": "python scripts/check.py"}',
}
pack("_base", base, description="Universal project standards")

python_common = {
    "pyproject.toml": """[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "{{ project_name }}"
version = "0.1.0"
description = "{{ project_name }} application"
readme = "README.md"
requires-python = ">=3.10"
dependencies = {{ dependencies | tojson }}

[project.optional-dependencies]
dev = ["pytest>=9.0.3", "ruff>=0.15", "httpx>=0.28"]

[project.scripts]
{{ package_name }} = "{{ package_name }}:main"

[tool.hatch.build.targets.wheel]
packages = ["src/{{ package_name }}"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
""",
    "src/{{ package_name }}/__init__.py": '''"""{{ project_name }} public API."""
__version__ = "0.1.0"


def greet(name: str) -> str:
    if not name.strip():
        raise ValueError("Name must not be empty")
    return f"Hello, {name.strip()}!"


def main() -> None:
    print(greet("world"))
''',
    "src/{{ package_name }}/__main__.py": "from . import main\n\nmain()",
    "main.py": 'from {{ package_name }} import main\n\nif __name__ == "__main__":\n    main()',
    "README.md": "# {{ project_name }}\n\nPython package. Install with `uv sync --extra dev`; run `uv run {{ package_name }}`. Run tests with `uv run pytest`.",
    ".python-version": "3.12",
    "pytest.ini": "[pytest]\npythonpath = src\ntestpaths = tests",
    "ruff.toml": 'line-length = 100\n[lint]\nselect = ["E4", "E7", "E9", "F"]',
    ".gitignore": "__pycache__/\n.venv/\n.pytest_cache/\n.ruff_cache/\ndist/\n.env",
    " tests/test_greeting.py".strip(): """import pytest
from {{ package_name }} import greet


def test_greeting_trims_name():
    assert greet(" Ada ") == "Hello, Ada!"


def test_greeting_requires_name():
    with pytest.raises(ValueError):
        greet(" ")
""",
    "Dockerfile": """FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && useradd --create-home app
USER app
CMD ["{{ package_name }}"]
""",
    ".dockerignore": ".git\n.venv\n__pycache__\n.env\n*.db",
}
for name, dependencies in [
    ("python", []),
    ("cli", ["typer>=0.27,<0.28"]),
    ("fastapi", ["fastapi>=0.128,<1", "uvicorn>=0.40,<1"]),
    ("ds", ["pandas>=2.2,<4", "numpy>=2,<3", "jupyterlab>=4,<5"]),
]:
    files = dict(python_common)
    # Defaults are literal per-stack; other context belongs to the project being rendered.
    files["pyproject.toml"] = files["pyproject.toml"].replace(
        "{{ dependencies | tojson }}", json.dumps(dependencies)
    )
    if name == "cli":
        files["src/{{ package_name }}/__init__.py"] = """import typer

app = typer.Typer()


def greet(name: str) -> str:
    if not name.strip():
        raise ValueError("Name must not be empty")
    return f"Hello, {name.strip()}!"


@app.command()
def hello(name: str = "world") -> None:
    typer.echo(greet(name))


def main() -> None:
    app()
"""
    if name == "fastapi":
        files["src/{{ package_name }}/api.py"] = """from fastapi import FastAPI

app = FastAPI(title="{{ project_name }}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
"""
        files["main.py"] = "from {{ package_name }}.api import app as app"
        files["tests/test_api.py"] = """from fastapi.testclient import TestClient
from {{ package_name }}.api import app


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}
"""
        files["Dockerfile"] = files["Dockerfile"].replace(
            'CMD ["{{ package_name }}"]',
            'EXPOSE 8000\nCMD ["uvicorn", "{{ package_name }}.api:app", "--host", "0.0.0.0", "--port", "8000"]',
        )
    if name == "ds":
        files["notebooks/exploration.ipynb"] = json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [
                            "# {{ project_name }}\nDocument data provenance before analysis."
                        ],
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        )
        files["data/README.md"] = (
            "Store raw datasets outside version control. Record provenance, licensing and transformations."
        )
    pack(
        name,
        files,
        description=f"{name} Python project",
        hooks=[{"argv": ["uv", "sync", "--extra", "dev"]}],
        next_steps=["uv sync --extra dev", "uv run pytest", "uv run ruff check ."],
    )

node_common = {
    "src/greeting.mjs": """export function greet(name) {
  if (!name.trim()) throw new Error('Name must not be empty');
  return `Hello, ${name.trim()}!`;
}
""",
    " tests/greeting.test.mjs".strip(): """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { greet } from '../src/greeting.mjs';

test('greeting trims names', () => assert.equal(greet(' Ada '), 'Hello, Ada!'));
test('blank names are rejected', () => assert.throws(() => greet(' ')));
""",
    ".gitignore": "node_modules/\ndist/\n.next/\n.env\n.env.*\n!.env.example",
    "README.md": "# {{ project_name }}\n\nInstall with `npm install`, then `npm test` and `npm run build`. See the root docs for runtime requirements.",
    ".nvmrc": "22",
    ".npmrc": "engine-strict=true\nfund=false",
    " tsconfig.json".strip(): json.dumps(
        {
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["DOM", "ES2022"],
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "jsx": "react-jsx",
                "strict": True,
                "allowJs": True,
                "skipLibCheck": True,
                "noEmit": True,
                "esModuleInterop": True,
                "resolveJsonModule": True,
            },
            "include": ["src", "app", "App.tsx"],
        },
        indent=2,
    ),
    "eslint.config.mjs": """import js from '@eslint/js';
export default [{ ignores: ['node_modules/**', 'dist/**', '.next/**'] }, js.configs.recommended, { languageOptions: { globals: { console: 'readonly', process: 'readonly', window: 'readonly', document: 'readonly' } } }];""",
    ".dockerignore": ".git\nnode_modules\n.next\ndist\n.env",
    "Dockerfile": """FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
FROM node:22-slim
WORKDIR /app
COPY --from=build --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["npm", "start"]
""",
}
for name in ["nextjs", "mern", "nestjs", "electron", "react-native"]:
    files = dict(node_common)
    package = {
        "name": "{{ project_name }}",
        "version": "0.1.0",
        "private": True,
        "type": "module",
        "engines": {"node": ">=22"},
        "scripts": {
            "test": "node --test tests/*.test.mjs",
            "lint": "eslint src/greeting.mjs tests/*.mjs",
            "typecheck": "tsc --noEmit",
        },
        "dependencies": {},
        "devDependencies": {
            "typescript": "^5.9.0",
            "@types/node": "^22.0.0",
            "eslint": "^9.0.0",
            "@eslint/js": "^9.0.0",
        },
    }
    if name == "nextjs":
        package["dependencies"] = {"next": "^16.0.0", "react": "^19.2.0", "react-dom": "^19.2.0"}
        package["devDependencies"].update(
            {"@types/react": "^19.0.0", "@types/react-dom": "^19.0.0"}
        )
        package["scripts"].update({"dev": "next dev", "build": "next build", "start": "next start"})
        files.update(
            {
                "app/layout.tsx": """import type { Metadata } from 'next';
import type { ReactNode } from 'react';
export const metadata: Metadata = { title: '{{ project_name }}', description: 'Built with Flunky' };
export default function Layout({ children }: { children: ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
""",
                "app/page.tsx": """import { greet } from '../src/greeting.mjs';
export default function Home() { return <main><h1>{{ project_name }}</h1><p>{greet('world')}</p></main>; }
""",
                "app/not-found.tsx": 'export default function NotFound() { return <main><h1>Page not found</h1><a href="/">Home</a></main>; }',
                "next.config.ts": "import type { NextConfig } from 'next';\nconst config: NextConfig = { output: 'standalone' };\nexport default config;",
                "next-env.d.ts": '/// <reference types="next" />\n/// <reference types="next/image-types/global" />',
            }
        )
    elif name == "mern":
        package["dependencies"] = {
            "express": "^5.1.0",
            "mongodb": "^6.0.0",
            "react": "^19.2.0",
            "react-dom": "^19.2.0",
        }
        package["devDependencies"].update(
            {"vite": "^7.0.0", "@types/react": "^19.0.0", "@types/react-dom": "^19.0.0"}
        )
        package["scripts"].update(
            {
                "dev": "vite --host 127.0.0.1",
                "build": "vite build",
                "start": "node server/index.mjs",
                "dev:api": "node --watch server/index.mjs",
            }
        )
        files.update(
            {
                "index.html": '<!doctype html><html lang="en"><meta charset="utf-8"><title>{{ project_name }}</title><div id="root"></div><script type="module" src="/src/main.tsx"></script></html>',
                "src/main.tsx": """import { createRoot } from 'react-dom/client';
import { greet } from './greeting.mjs';
createRoot(document.getElementById('root')!).render(<main><h1>{{ project_name }}</h1><p>{greet('world')}</p></main>);""",
                "server/index.mjs": """import express from 'express';
const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '100kb' }));
app.get('/health', (_request, response) => response.json({ status: 'ok' }));
app.use(express.static('dist'));
app.listen(Number(process.env.PORT || 3000), '0.0.0.0');
""",
                "server/database.mjs": """import { MongoClient } from 'mongodb';
export async function connectDatabase() {
  if (!process.env.MONGODB_URI) throw new Error('Set MONGODB_URI');
  const client = new MongoClient(process.env.MONGODB_URI);
  await client.connect();
  return client;
}
""",
                ".env.example": "PORT=3000\nMONGODB_URI=mongodb://localhost:27017/{{ package_name }}",
                "vite.config.ts": "import { defineConfig } from 'vite';\nexport default defineConfig({ server: { proxy: { '/health': 'http://localhost:3000' } } });",
            }
        )
    elif name == "nestjs":
        package.pop("type")
        package["dependencies"] = {
            "@nestjs/common": "^11.0.0",
            "@nestjs/core": "^11.0.0",
            "@nestjs/platform-express": "^11.0.0",
            "reflect-metadata": "^0.2.2",
            "rxjs": "^7.8.0",
        }
        package["scripts"].update(
            {"dev": "tsc --watch", "build": "tsc", "start": "node dist/main.js"}
        )
        files.update(
            {
                "src/main.ts": """import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './module';
async function bootstrap() { const app = await NestFactory.create(AppModule); await app.listen(Number(process.env.PORT || 3000), '0.0.0.0'); }
void bootstrap();""",
                "src/module.ts": """import { Controller, Get, Module } from '@nestjs/common';
@Controller()
class HealthController { @Get('health') health() { return { status: 'ok' }; } }
@Module({ controllers: [HealthController] })
export class AppModule {}""",
                "tsconfig.json": json.dumps(
                    {
                        "compilerOptions": {
                            "module": "CommonJS",
                            "target": "ES2022",
                            "outDir": "dist",
                            "rootDir": "src",
                            "experimentalDecorators": True,
                            "emitDecoratorMetadata": True,
                            "strict": True,
                            "esModuleInterop": True,
                            "skipLibCheck": True,
                        },
                        "include": ["src/**/*.ts"],
                    },
                    indent=2,
                ),
            }
        )
    elif name == "electron":
        package["main"] = "electron/main.cjs"
        package["devDependencies"]["electron"] = "^44.5.1"
        package["scripts"].update(
            {"dev": "electron .", "start": "electron .", "build": "node scripts/build.mjs"}
        )
        files.update(
            {
                "electron/main.cjs": """const { app, BrowserWindow } = require('electron');
const path = require('node:path');
function openWindow() {
  const window = new BrowserWindow({ width: 1000, height: 700, webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } });
  window.loadFile(path.join(__dirname, '../index.html'));
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
}
app.whenReady().then(openWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (!BrowserWindow.getAllWindows().length) openWindow(); });""",
                "index.html": """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'"><title>{{ project_name }}</title></head><body><h1>{{ project_name }}</h1><p id="greeting"></p><script type="module" src="src/renderer.mjs"></script></body></html>""",
                "src/renderer.mjs": "import { greet } from './greeting.mjs';\ndocument.getElementById('greeting').textContent = greet('world');",
                "scripts/build.mjs": "import { cpSync, mkdirSync } from 'node:fs';\nmkdirSync('dist', { recursive: true });\nfor (const source of ['electron', 'src', 'index.html', 'package.json']) cpSync(source, `dist/${source}`, { recursive: true });",
            }
        )
    else:
        package["main"] = "index.js"
        package["dependencies"] = {"expo": "~57.0.26", "react": "19.2.3", "react-native": "0.86.3"}
        package["devDependencies"]["@types/react"] = "^19.2.0"
        package["scripts"].update(
            {"dev": "expo start", "start": "expo start", "build": "tsc --noEmit"}
        )
        files.update(
            {
                "index.js": "import { registerRootComponent } from 'expo';\nimport App from './App';\nregisterRootComponent(App);",
                "App.tsx": """import { SafeAreaView, Text } from 'react-native';
export default function App() { return <SafeAreaView><Text>{{ project_name }}</Text></SafeAreaView>; }""",
                "app.json": '{"expo":{"name":"{{ project_name }}","slug":"{{ project_name }}","version":"0.1.0"}}',
                "tsconfig.json": '{"extends":"expo/tsconfig.base","compilerOptions":{"strict":true}}',
            }
        )
    files["package.json"] = json.dumps(package, indent=2)
    pack(
        name,
        files,
        description=f"{name} application",
        hooks=[{"argv": ["npm", "install"]}],
        next_steps=["npm install", "npm test", "npm run build"],
    )

pack(
    "flutter",
    {
        "pubspec.yaml": """name: {{ package_name }}
description: {{ project_name }} application
publish_to: none
version: 0.1.0+1
environment:
  sdk: '>=3.6.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0
flutter:
  uses-material-design: true
""",
        "lib/main.dart": """import 'package:flutter/material.dart';
void main() => runApp(const StarterApp());
class StarterApp extends StatelessWidget {
  const StarterApp({super.key});
  @override
  Widget build(BuildContext context) => const MaterialApp(home: Scaffold(body: Center(child: Text('{{ project_name }}'))));
}
""",
        " test/widget_test.dart".strip(): """import 'package:flutter_test/flutter_test.dart';
import 'package:{{ package_name }}/main.dart';
void main() { testWidgets('shows the project name', (tester) async { await tester.pumpWidget(const StarterApp()); expect(find.text('{{ project_name }}'), findsOneWidget); }); }
""",
        "analysis_options.yaml": "include: package:flutter_lints/flutter.yaml",
        "README.md": "# {{ project_name }}\n\nRun `flutter create --platforms=android,ios,web .` once to generate native platform wrappers, then `flutter pub get`, `flutter analyze`, and `flutter test`. Native SDK/signing setup is separate.",
        ".gitignore": ".dart_tool/\nbuild/\n.flutter-plugins-dependencies\n.env",
    },
    description="Flutter application with tested widget entry point",
    hooks=[{"argv": ["flutter", "pub", "get"]}],
    next_steps=[
        "flutter create --platforms=android,ios,web .",
        "flutter pub get",
        "flutter analyze",
        "flutter test",
    ],
)
