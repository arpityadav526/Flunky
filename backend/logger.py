"""Compatibility logger; new modules use structlog with request context."""

import logging

logger = logging.getLogger("flunky")
