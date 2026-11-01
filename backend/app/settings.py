from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore")
    evidence_directory: str | None = None
    app_env: str = "development"
    database_url: SecretStr
    session_secret: SecretStr
    auth_issuer: str = "aroundyou-local"
    auth_audience: str = "aroundyou-api"

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value):
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL psycopg URL required")
        return value

    @field_validator("session_secret")
    @classmethod
    def strong_secret(cls, value):
        if len(value.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        return value
