"""Create distribution manifests from actual release binaries, never placeholder hashes."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]*)", args.version) or not re.fullmatch(
        r"[\w.-]+/[\w.-]+", args.repository
    ):
        parser.error("Invalid version or repository")
    root = args.directory
    names = ["flunky-macos-arm64", "flunky-macos-x64", "flunky-windows-x64.exe"]
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    base = f"https://github.com/{args.repository}/releases/download/v{args.version}"
    (root / "SHA256SUMS").write_text(
        "".join(f"{value}  {name}\n" for name, value in hashes.items())
    )
    formula = f'''class Flunky < Formula
  desc "Developer tasks and project scaffolding"
  homepage "https://github.com/{args.repository}"
  version "{args.version}"
  license "MIT"
  on_macos do
    on_arm do
      url "{base}/{names[0]}"
      sha256 "{hashes[names[0]]}"
    end
    on_intel do
      url "{base}/{names[1]}"
      sha256 "{hashes[names[1]]}"
    end
  end
  def install
    bin.install Dir["flunky-macos-*"][0] => "flunky"
  end
  test do
    assert_match version.to_s, shell_output("#{{bin}}/flunky --version")
  end
end
'''
    (root / "flunky.rb").write_text(formula)
    (root / "flunky.scoop.json").write_text(
        json.dumps(
            {
                "version": args.version,
                "description": "Developer tasks and project scaffolding",
                "homepage": f"https://github.com/{args.repository}",
                "license": "MIT",
                "architecture": {
                    "64bit": {"url": f"{base}/{names[2]}#/flunky.exe", "hash": hashes[names[2]]}
                },
                "bin": "flunky.exe",
            },
            indent=2,
        )
    )
    (root / "Flunky.Flunky.yaml").write_text(f"""PackageIdentifier: Flunky.Flunky
PackageVersion: {args.version}
PackageLocale: en-US
Publisher: Flunky contributors
PackageName: Flunky
License: MIT
ShortDescription: Developer tasks and project scaffolding
Installers:
  - Architecture: x64
    InstallerType: portable
    Commands:
      - flunky
    InstallerUrl: {base}/{names[2]}
    InstallerSha256: {hashes[names[2]].upper()}
ManifestType: singleton
ManifestVersion: 1.6.0
""")


if __name__ == "__main__":
    main()
