"""Container startup: migrate before accepting traffic, then forward signals directly."""

import os
import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    # The limiter is process-local: keep one worker until a shared adapter exists.
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "backend.main:app",
            "--worker-class",
            "uvicorn_worker.UvicornWorker",
            "--workers",
            "1",
            "--bind",
            "0.0.0.0:8000",
            "--access-logfile",
            "-",
        ],
    )


if __name__ == "__main__":
    main()
