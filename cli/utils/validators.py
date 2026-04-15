from pathlib import Path


def validate_project_name(name: str) -> str:
    cleaned = name.strip().lower()
    if not cleaned:
        raise ValueError("Project name cannot be empty.")
    return cleaned


def validate_project_path(path: str) -> Path:
    project_path = Path(path).expanduser().resolve()
    if not project_path.exists():
        raise ValueError(f"Path does not exist: {project_path}")
    if not project_path.is_dir():
        raise ValueError(f"Path is not a directory: {project_path}")
    return project_path