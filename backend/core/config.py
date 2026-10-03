from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "production"] = "dev"
    secret_key: str = "dev-secret-change-me"
    database_url: str = "sqlite+aiosqlite:///./flunky.db"
    sql_echo: bool = False
    access_token_expire_minutes: int = 15
    sentry_dsn: str | None = None

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.environment == "production" and (
            self.secret_key == "dev-secret-change-me" or len(self.secret_key) < 32
        ):
            raise ValueError(
                "Set SECRET_KEY to a random secret of at least 32 characters in production"
            )
        if self.database_url.startswith("sqlite://"):
            self.database_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        elif self.database_url.startswith(("postgres://", "postgresql://")):
            self.database_url = "postgresql+asyncpg://" + self.database_url.split("://", 1)[1]
        return self


settings = Settings()
