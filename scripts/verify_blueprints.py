"""Exhaustively generate all stack/type/add-on subsets in temporary directories."""

import argparse
import ast
import itertools
import json
import shutil
import tempfile
from pathlib import Path

from cli.services.scaffold import ADDONS, STACKS, TYPES, plan_project, write_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", choices=STACKS)
    args = parser.parse_args()
    count = 0
    with tempfile.TemporaryDirectory(prefix="flunky-blueprints-") as directory:
        target = Path(directory) / "demo"
        for stack, kind, bits in itertools.product(
            (args.stack,) if args.stack else STACKS,
            TYPES,
            itertools.product((False, True), repeat=len(ADDONS)),
        ):
            addons = tuple(addon for addon, enabled in zip(ADDONS, bits) if enabled)
            files, _, _ = plan_project(stack, "demo", kind, addons)
            write_files(target, files)
            for path in target.rglob("*"):
                if path.suffix == ".py":
                    ast.parse(path.read_text(encoding="utf-8"))
                elif path.suffix in {".json", ".ipynb"}:
                    json.loads(path.read_text(encoding="utf-8"))
            shutil.rmtree(target)
            count += 1
            if count % 1280 == 0:
                print(f"PASS {stack}: {count} generated combinations", flush=True)
    print(f"PASS {count} stack × type × add-on combinations")


if __name__ == "__main__":
    main()
