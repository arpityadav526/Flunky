"""Mail delivery boundary. The development console reports a private mailbox file."""

import json
import os
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import structlog
from platformdirs import user_data_path


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, token: str) -> None: ...


class ConsoleMailer:
    def send(self, recipient: str, subject: str, token: str) -> None:
        directory = Path(
            os.environ.get("FLUNKY_MAILBOX_DIR", str(user_data_path("flunky") / "mailbox"))
        )
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / f"{uuid4()}.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"to": recipient, "subject": subject, "token": token}, output)
        structlog.get_logger().info("development_email", mailbox=str(path))


mailer: Mailer = ConsoleMailer()
