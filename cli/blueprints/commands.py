"""Project generation commands and previews."""

import difflib
from pathlib import Path

import typer
from rich.tree import Tree

from cli import ui
from cli.services import scaffold
from cli.ui.commands import FlunkyGroup
from cli.ui.prompts import questionary


def preview(files: dict[str, str], target: Path) -> None:
    tree = Tree(str(target))
    for path, content in sorted(files.items()):
        tree.add(f"{path} ({len(content.encode())} bytes)")
    ui.console.print(tree)


def register_blueprints(app: typer.Typer) -> None:
    @app.command("init")
    def init_project(
        name: str | None = typer.Argument(None),
        legacy_stack: str | None = typer.Argument(None, hidden=True),
        legacy_name: str | None = typer.Argument(None, hidden=True),
        stack: str | None = typer.Option(
            None,
            help="python, cli, fastapi, ds, nextjs, mern, nestjs, electron, react-native, flutter; or a user template name.",
        ),
        project_type: str = typer.Option(
            "app", "--type", help="app, fullstack, monorepo, library, cli."
        ),
        addons: str = typer.Option(
            "",
            help="Comma-separated: docker, ci, database, auth, linting, docs-site, testing, monorepo.",
        ),
        license_name: str = typer.Option("MIT", "--license", help="MIT or UNLICENSED."),
        dry_run: bool = typer.Option(False),
        install: bool = typer.Option(
            False, help="Install dependencies using checked, timed commands."
        ),
        git: bool = typer.Option(False, help="Initialize Git and create the first commit."),
        open_editor: bool = typer.Option(
            False, "--open", help="Open the generated project in VS Code."
        ),
        trust_template: bool = typer.Option(
            False, help="Explicitly trust installation hooks from a user template."
        ),
    ) -> None:
        """Generate a project. Example: flunky init demo --stack fastapi --type fullstack --yes."""
        if name == "create" and legacy_stack and legacy_name:
            # Preserve the original command and service boundary for existing integrations.
            ui.console.print(
                "`init create STACK NAME` is deprecated; use `init NAME --stack STACK`."
            )
            path = scaffold.scaffold_project(legacy_stack, legacy_name)
            ui.output({"path": path}, f"Project created at {path}")
            return
        if legacy_stack or legacy_name:
            raise scaffold.ScaffoldError(
                "Unexpected arguments. Try `flunky init demo --stack python`."
            )
        wizard = name is None
        if name is None:
            name = questionary.text("Project name", default="my-app").ask()
        if stack is None:
            stack = (
                "python"
                if ui.state.yes
                else questionary.select("Stack", choices=list(scaffold.STACKS)).ask()
            )
        if not name or not stack:
            raise typer.Abort()
        if wizard and not ui.state.yes:
            project_type = questionary.select(
                "Project layout", choices=list(scaffold.TYPES), default=project_type
            ).ask()
            addons = questionary.text("Add-ons (comma-separated)", default=addons).ask() or ""
            license_name = questionary.select(
                "License", choices=["MIT", "UNLICENSED"], default=license_name
            ).ask()
            if not project_type or not license_name:
                raise typer.Abort()
        files, hooks, steps = scaffold.plan_project(
            stack,
            name,
            project_type,
            tuple(filter(None, (s.strip() for s in addons.split(",")))),
            license_name,
        )
        target = Path(name).absolute()
        if dry_run:
            preview(files, target)
            ui.output(
                {
                    "path": str(target),
                    "files": list(files),
                    "bytes": sum(len(s.encode()) for s in files.values()),
                    "dry_run": True,
                }
            )
            return
        if install and stack not in scaffold.STACKS and not trust_template:
            raise scaffold.ScaffoldError(
                "User-template hooks require --trust-template with --install. Inspect the manifest first."
            )
        allow = ui.state.yes
        if target.exists() and any(target.iterdir()) and not allow:
            allow = bool(
                questionary.confirm(
                    "Directory is not empty. Add missing files only?", default=False
                ).ask()
            )
        if git and (target / ".git").exists():
            raise scaffold.ScaffoldError(
                "A Git repository already exists here. Commit changes yourself."
            )
        if install and target.exists() and any((target / path).exists() for path in files):
            raise scaffold.ScaffoldError(
                "Install hooks require a fresh target so existing scripts cannot run unexpectedly."
            )
        written = scaffold.write_files(target, files, allow_existing=allow)
        if install:
            for prefix, hook in hooks:
                scaffold.run_hook(target / prefix, hook)
        if git:
            for args in (
                ["git", "init"],
                ["git", "add", "--", *written],
                ["git", "commit", "-m", "chore: initialize project"],
            ):
                scaffold.run_hook(target, scaffold.Hook(argv=args))
        if open_editor:
            scaffold.run_hook(target, scaffold.Hook(argv=["code", str(target)]))
        ui.output(
            {
                "path": str(target),
                "created": written,
                "skipped": sorted(set(files) - set(written)),
                "next_steps": steps,
            },
            f"Created {len(written)} files in {target}\nNext steps:\n" + "\n".join(steps),
        )

    structure = typer.Typer(
        cls=FlunkyGroup, help="Apply project standards. Example: flunky structure apply . --yes"
    )
    app.add_typer(structure, name="structure")

    @structure.command("apply")
    def apply_structure(
        directory: Path = typer.Argument(...), dry_run: bool = typer.Option(False)
    ) -> None:
        """Add missing standard files and preserve existing content. Example: flunky structure apply . --dry-run."""
        if not directory.is_dir():
            raise scaffold.ScaffoldError("Choose an existing project directory.")
        context = {
            "project_name": directory.resolve().name,
            "stack": "existing",
            "project_type": "existing",
            "blueprint_version": "1.0.0",
            "next_steps": "python scripts/check.py",
            "validation": "python scripts/check.py",
            "layout": "Existing layout is preserved.",
            "ci_steps": "",
        }
        files = scaffold.render_layer(scaffold.TEMPLATES_DIR / "_base", context)
        conflicts = []
        for path, content in files.items():
            dest = directory / path
            if (
                dest.is_file()
                and not dest.is_symlink()
                and dest.read_text(encoding="utf-8") != content
            ):
                conflicts.append(path)
                ui.console.print(
                    "".join(
                        difflib.unified_diff(
                            dest.read_text(encoding="utf-8").splitlines(True),
                            content.splitlines(True),
                            fromfile=path,
                            tofile=f"proposed/{path}",
                        )
                    ),
                    markup=False,
                )
                if not ui.state.yes and not dry_run:
                    if not questionary.confirm(
                        f"Keep existing {path} and continue?", default=True
                    ).ask():
                        raise typer.Abort()
        if dry_run:
            preview(files, directory)
            written: list[str] = []
        else:
            written = scaffold.write_files(directory, files, allow_existing=True)
        ui.output(
            {"created": written, "preserved": conflicts, "dry_run": dry_run},
            f"Added {len(written)} files; preserved {len(conflicts)} conflicting files.",
        )
