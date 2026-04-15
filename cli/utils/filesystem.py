from pathlib import Path


CONFIG_DIR = Path.home() / ".flunky"
PROJECTS_FILE = CONFIG_DIR / "projects.json"


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_projects_file() -> Path:
    ensure_config_dir()
    return PROJECTS_FILE