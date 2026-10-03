# Project blueprints

```sh
flunky init my-app --stack fastapi --type fullstack --addons docker,ci --license MIT --yes
flunky init preview --stack nextjs --dry-run
flunky structure apply existing-project --dry-run
flunky structure apply existing-project --yes
```

Every project receives contributing/security policies, license, docs, portable checks, GitHub workflow/templates, pre-commit and devcontainer configuration. Stack templates include working entry points and tests. `app`, `fullstack`, `monorepo`, `library`, and `cli` select the layout. `single-app` is accepted as an alias. `init create STACK NAME` remains a deprecated alias.

Use `--install`, `--git`, or `--open` to run dependency installation, initialize/commit a repository, or open VS Code. These commands need the relevant local tools. Failures leave generated files available for inspection. Installation executes dependency-manager lifecycle scripts: review third-party dependencies and templates before opting in.

Existing files are preserved. Nonempty targets require confirmation (`--yes` for scripts). `structure apply` shows differing content and asks whether to keep it and continue; it never replaces existing content. Dry runs write nothing.

Add-ons: `docker`/`database` add a Postgres 16 Compose service with a required password; `docs-site` adds MkDocs Material configuration; `monorepo` adds apps and shared packages. `ci`, `linting`, and `testing` acknowledge capabilities already included in the baseline. `auth` adds an integration guide; it does **not** install or enable authentication. Review generated security policies and dependency locks before deployment.

Store a custom template in `<Flunky config directory>/templates/NAME/` with a `manifest.json` and UTF-8 Jinja files. The bundled manifests are examples of schema version 1. Context includes `project_name`, `package_name`, `stack`, `project_type`, `blueprint_version`, `layout`, `next_steps`, `validation`, and `ci_steps`. Sources/destinations must be portable relative paths; no traversal or symlink escapes. Hooks are `{"argv":["program","argument"],"timeout":300}`. Custom installation requires `--install --trust-template`; `--yes` alone does not authorize hooks.

Flutter generates the application/widget tests, then its official SDK creates platform wrappers. Electron produces runtime sources; packaging/signing is separate. React Native uses Expo; native signing/builds require platform setup. A library layout does not automatically turn an application framework into a publishable ecosystem package.

Run `python -m scripts.verify_blueprints` to generate and parse all 12,800 stack/layout/add-on subsets in temporary directories. The regular suite covers 500 representative combinations. Ecosystem install/lint/build checks are separate from structural verification.
