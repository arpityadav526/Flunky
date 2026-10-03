"""Compatibility exports for the original backend imports."""

from backend.core.config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
DATABASE_URL = settings.database_url
SQL_ECHO = settings.sql_echo
