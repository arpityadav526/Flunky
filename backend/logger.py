import logging
import os
from logging.handlers import RotatingFileHandler

from backend.config import DATABASE_URL  # optional if you want config import initialized

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "flunky.log")

os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("flunky")
    logger.setLevel(LOG_LEVEL)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1024 * 1024,
        backupCount=3,
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger


logger = setup_logger()