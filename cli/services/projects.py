import json
from pathlib import Path
from typing import Dict

from cli.utils.filesystem import get_projects_file
from cli.utils.validators import validate_project_name, validate_project_path


def load_projects() -> Dict[str, str]:
    projects_file = get_projects_file()

    if not projects_file.exists():
        return {}

    try:
        with open(projects_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("projects", {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_projects(projects: Dict[str, str]) -> None:
    projects_file = get_projects_file()
    data = {"projects": projects}

    with open(projects_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def add_project(name: str, path: str) -> tuple[str, str]:
    project_name = validate_project_name(name)
    project_path = validate_project_path(path)

    projects = load_projects()
    projects[project_name] = str(project_path)
    save_projects(projects)

    return project_name, str(project_path)


def remove_project(name: str) -> str:
    project_name = validate_project_name(name)
    projects = load_projects()

    if project_name not in projects:
        raise ValueError(f"Project '{project_name}' not found.")

    del projects[project_name]
    save_projects(projects)

    return project_name


def list_projects() -> Dict[str, str]:
    return load_projects()


def get_project_path(name: str) -> Path:
    project_name = validate_project_name(name)
    projects = load_projects()

    if project_name not in projects:
        raise ValueError(f"Project '{project_name}' not found.")

    return Path(projects[project_name])