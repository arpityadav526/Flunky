"""Generate local deployment credentials without overwriting existing secrets."""

import os
import secrets
from pathlib import Path


def main() -> None:
    path = Path(".env.docker")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Keeping existing .env.docker credentials.")
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(f"SECRET_KEY={secrets.token_hex(32)}\n")
        output.write(f"POSTGRES_PASSWORD={secrets.token_hex(32)}\n")
    print("Created .env.docker. Keep this file private and backed up.")


if __name__ == "__main__":
    main()
