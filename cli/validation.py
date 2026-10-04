"""Account input rules matching the API, with messages safe to display."""

import re

from email_validator import EmailNotValidError, validate_email


def username_error(value: str) -> str | None:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,50}", value):
        return "Username must be 3–50 characters: letters, numbers, underscores or hyphens (no spaces)."
    return None


def password_error(value: str) -> str | None:
    if not 8 <= len(value) <= 1024:
        return "Password must be 8–1024 characters."
    return None


def email_error(value: str) -> str | None:
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError:
        return "Enter a valid email address, such as name@example.com."
    return None
