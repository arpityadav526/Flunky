import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cli.services import projects, scaffold
from cli.utils.validators import is_valid_project_name, validate_project_name, validate_project_path


@pytest.mark.parametrize("stack", scaffold.STACKS)
@pytest.mark.parametrize("kind", scaffold.TYPES)
@pytest.mark.parametrize("addons", [(), *[(a,) for a in scaffold.ADDONS], scaffold.ADDONS])
def test_every_template(stack, kind, addons, tmp_path):
    import ast

    files, _, steps = scaffold.plan_project(stack, "demo", kind, addons)
    target = tmp_path / "demo"
    written = scaffold.write_files(target, files)
    assert len(written) == len(files)
    assert steps
    for path in target.rglob("*"):
        if path.suffix == ".py":
            ast.parse(path.read_text())
        if path.suffix in {".json", ".ipynb"}:
            json.loads(path.read_text())
    assert (target / "LICENSE").is_file()
    assert (target / "scripts/check.py").is_file()


def test_missing_templates(tmp_path):
    with pytest.raises(scaffold.ScaffoldError, match="not found"):
        scaffold.scaffold_project("missing", "demo")
    with pytest.raises(scaffold.ScaffoldError, match="Manifest"):
        scaffold.load_manifest(tmp_path)


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=50))
def test_valid_names(name):
    assert is_valid_project_name(name)
    assert validate_project_name(name) == name


def test_project_validation(tmp_path, monkeypatch):
    from cli.utils import filesystem

    monkeypatch.setattr(filesystem, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(filesystem, "PROJECTS_FILE", tmp_path / "projects.json")
    with pytest.raises(ValueError):
        validate_project_name(" ")
    f = tmp_path / "file"
    f.touch()
    with pytest.raises(ValueError, match="not a directory"):
        validate_project_path(str(f))
    with pytest.raises(ValueError, match="not found"):
        projects.get_project_path("missing")
    projects.add_project("demo", str(tmp_path))
    assert projects.get_project_path("demo") == tmp_path
    filesystem.PROJECTS_FILE.write_text("broken")
    assert projects.load_projects() == {}


@pytest.mark.parametrize(
    "path", ["../bad", "/bad", "a/../b", "a\\b", "CON", "nul.txt", "a:", "a.", "x/", "x" * 101]
)
def test_unsafe_paths(path):
    with pytest.raises(scaffold.ScaffoldError):
        scaffold.safe_path(path)


def test_preserve_and_symlink(tmp_path):
    target = tmp_path / "demo"
    target.mkdir()
    (target / "README.md").write_text("precious")
    with pytest.raises(scaffold.ScaffoldError, match="not empty"):
        scaffold.write_files(target, {"README.md": "replacement"})
    assert scaffold.write_files(
        target, {"README.md": "replacement", "a/b": "new"}, allow_existing=True
    ) == ["a/b"]
    assert (target / "README.md").read_text() == "precious"
    (target / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(scaffold.ScaffoldError, match="symbolic"):
        scaffold.write_files(target, {"link/file": "bad"}, allow_existing=True)


def test_hooks_checked(tmp_path, monkeypatch):
    import subprocess
    from unittest.mock import Mock

    run = Mock()
    monkeypatch.setattr(scaffold.subprocess, "run", run)
    scaffold.run_hook(tmp_path, scaffold.Hook(argv=["echo", "hi"]))
    assert run.call_args.kwargs["check"] is True
    assert "shell" not in run.call_args.kwargs
    run.side_effect = subprocess.TimeoutExpired("test", 1)
    with pytest.raises(scaffold.ScaffoldError, match="preserved"):
        scaffold.run_hook(tmp_path, scaffold.Hook(argv=["test"]))


def test_blueprint_commands(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from cli.main import app

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["init", "demo", "--stack", "fastapi", "--type", "fullstack", "--dry-run", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "demo").exists()
    assert json.loads(result.output)["dry_run"]
    result = runner.invoke(app, ["init", "demo", "--stack", "python", "--yes", "--json"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo/LICENSE").is_file()
    (tmp_path / "demo/README.md").write_text("custom")
    result = runner.invoke(app, ["structure", "apply", "demo", "--yes", "--json"])
    assert result.exit_code == 0, result.output
    assert "README.md" in json.loads(result.output)["preserved"]
    assert (tmp_path / "demo/README.md").read_text() == "custom"
    for args in (
        ["init", "../bad", "--yes"],
        ["init", "demo", "--stack", "missing"],
        ["structure", "apply", "missing"],
        ["init", "demo", "oops"],
    ):
        assert runner.invoke(app, args).exit_code != 0


def test_user_template_trust_and_validation(tmp_path, monkeypatch):
    from unittest.mock import Mock

    from typer.testing import CliRunner

    from cli import config
    from cli.main import app

    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    folder = config.CONFIG_DIR / "templates" / "custom"
    folder.mkdir(parents=True)
    (folder / "hello.j2").write_text("Hello {{ project_name }}")
    manifest = {
        "schema_version": 1,
        "version": "1.0.0",
        "name": "custom",
        "description": "custom",
        "files": [{"src": "hello.j2", "dest": "hello.txt"}],
        "post_create": [{"argv": ["echo", "hello"]}],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "demo", "--stack", "custom", "--install", "--yes"]).exit_code
        == 1
    )
    assert not (tmp_path / "demo").exists()
    run = Mock()
    monkeypatch.setattr(scaffold.subprocess, "run", run)
    result = runner.invoke(
        app,
        [
            "init",
            "demo",
            "--stack",
            "custom",
            "--install",
            "--trust-template",
            "--git",
            "--open",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output
    assert run.call_count == 5
    manifest["files"][0]["dest"] = "../escape"
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(scaffold.ScaffoldError):
        scaffold.plan_project("custom", "demo")
    for kwargs in (
        {"project_type": "missing"},
        {"addons": ("missing",)},
        {"license_name": "missing"},
    ):
        with pytest.raises(scaffold.ScaffoldError):
            scaffold.plan_project("python", "demo", **kwargs)
    assert (
        "All rights reserved"
        in scaffold.plan_project("python", "demo", license_name="UNLICENSED")[0]["LICENSE"]
    )
