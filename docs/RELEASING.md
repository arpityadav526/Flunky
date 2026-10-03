# Release procedure

## Before the first public release

Confirm ownership/availability of the PyPI project name `flunky`. Configure a PyPI Trusted Publisher for the GitHub repository, workflow `release.yml`, and environment `pypi`; protect that GitHub environment with a reviewer. Trusted Publishing uses OIDC instead of a long-lived upload token ([PyPI guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/)). Do not publish under a name you do not control.

Enable Actions permissions for release-please to create pull requests. Conventional commits drive its version/changelog PR, including pyproject.toml and cli/_version.py. Merging a release PR triggers package/binary builds in the same workflow; this avoids relying on a new workflow being triggered by a GITHUB_TOKEN-created release. `workflow_dispatch` builds reviewable artifacts without publishing.

The release workflow tests Python code, builds a wheel/sdist and SBOM, and builds macOS arm64, macOS x64 and Windows x64 executables on their respective runners. Publishing waits for package and binary jobs. Configure CI branch protection and require all OS/Python jobs before merging. Hosted workflows have not been executed from this local session.

## Local rehearsal

```sh
uv sync --extra dev --extra test --extra docs --extra release
uv run python -m scripts.generate_help
uv run python -m scripts.generate_docs
uv run mkdocs build --strict
uv build
uv run python -m scripts.build_binary
uv run cyclonedx-py environment --output-file dist/sbom.cdx.json
```

Install the wheel in a clean venv, run the CLI surface verifier against an isolated server, and inspect the SBOM. The SBOM describes the build environment, including tooling; it is not a minimal runtime-only bill of materials. PyInstaller's standalone binary has different extraction/startup costs from the Python console entry point; the 150ms target applies to the installed Python CLI.

## Signing

Local binaries are unsigned/ad-hoc signed; the workflow does not claim Developer ID or Windows publisher signing. Before broad binary distribution, use an Apple Developer account, Developer ID Application certificate/private key, and notarization credentials. Build on the target architecture, sign with hardened runtime using PyInstaller's `--codesign-identity`, submit a ZIP with `xcrun notarytool submit --wait`, and distribute the notarized artifact. A bare executable cannot be stapled like an app bundle; package it appropriately if offline Gatekeeper validation is required. Verify signing/notarization on a clean Mac. Never commit certificates or credentials.

For Windows publisher identity, obtain a code-signing certificate or managed signing service, sign the final executable, and verify with `signtool verify /pa`. These accounts and credentials must be provided by the maintainer. Hashes and manifests must be generated **after** signing because signing changes the bytes. The initial automated pipeline emits unsigned artifacts; add signing before its artifact upload step when credentials are ready.

## Homebrew, Scoop and winget

`scripts/distribution_manifests.py` requires all three actual binaries and produces SHA256SUMS, a Homebrew formula, a Scoop JSON manifest and a winget singleton manifest. It refuses missing binaries rather than inserting dummy hashes. Release assets include these files. Validate the generated manifests with their native tools before publishing to public indexes.

Create a Homebrew tap repository, set `HOMEBREW_TAP` to owner/repository, and grant a narrowly scoped `HOMEBREW_TAP_TOKEN` permission to update that repository. The optional tap job installs the generated formula there after release assets exist. Scoop bucket/winget community submissions remain maintainer actions; no repository ownership or submission is assumed.

Enable GitHub Pages or another host for the built MkDocs artifact if a public docs site is desired. Configure a domain only after choosing the host. Public PyPI installation, Homebrew installation, native signing and hosted CI are release gates until independently verified.
