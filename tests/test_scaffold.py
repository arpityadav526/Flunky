import json
from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cli.services import projects, scaffold
from cli.utils.validators import is_valid_project_name, validate_project_name, validate_project_path


@pytest.mark.parametrize("stack", sorted(p.name for p in scaffold.TEMPLATES_DIR.iterdir()))
def test_every_template(stack, tmp_path, monkeypatch):
    run = Mock()
    monkeypatch.setattr(scaffold.subprocess, "run", run)
    target = tmp_path / "demo"
    assert scaffold.scaffold_project(stack, "demo", str(target)) == str(target)
    manifest = json.loads((scaffold.TEMPLATES_DIR / stack / "manifest.json").read_text())
    for spec in manifest["files"]:
        assert (target / spec["dest"]).is_file()
        assert "{{" not in (target / spec["dest"]).read_text()
    assert run.call_count == len(manifest["post_create"])


def test_missing_templates(tmp_path, monkeypatch):
    with pytest.raises(scaffold.ScaffoldError, match="not found"):
        scaffold.scaffold_project("missing", "demo")
    (tmp_path / "missing").mkdir()
    monkeypatch.setattr(scaffold, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(scaffold.ScaffoldError, match="Manifest"):
        scaffold.scaffold_project("missing", "demo")


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
