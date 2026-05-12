import os
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import subprocess

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

class ScaffoldError(Exception):
    pass

def scaffold_project(project_type: str, project_name: str, target_dir: str = None):
    template_dir = TEMPLATES_DIR / project_type
    if not template_dir.exists():
        raise ScaffoldError(f"Template '{project_type}' not found.")
    manifest_path = template_dir / "manifest.json"
    if not manifest_path.exists():
        raise ScaffoldError(f"Manifest for '{project_type}' not found.")
    with open(manifest_path) as f:
        manifest = json.load(f)
    project_dir = Path(target_dir or project_name).absolute()
    os.makedirs(project_dir, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    context = {"project_name": project_name}
    for file in manifest["files"]:
        src = file["src"]
        dest = project_dir / file["dest"]
        template = env.get_template(src)
        with open(dest, "w") as out_f:
            out_f.write(template.render(context))
    # Post-create hooks
    for cmd in manifest.get("post_create", []):
        subprocess.run(cmd, shell=True, cwd=project_dir)
    return str(project_dir)
