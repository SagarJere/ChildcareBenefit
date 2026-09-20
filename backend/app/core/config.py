"""Application configuration loaded from environment variables.

Settings are grouped by concern (app, CORS, database, MinIO, logging) and are
populated exclusively from environment variables / a local .env file. No
secret or connection value is ever hardcoded here.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Childcare Benefit API"
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    api_v1_prefix: str = "/api/v1"

    # --- CORS ---
    cors_allowed_origins: str = Field(default="http://localhost:5173")

    # --- SQL Server ---
    # "sql" authenticates with mssql_username/mssql_password. "windows" uses
    # an ODBC trusted connection under the identity running the backend
    # process instead, and ignores mssql_username/mssql_password.
    mssql_auth_mode: Literal["sql", "windows"] = Field(default="sql")
    mssql_server: str = Field(default="")
    # Leave unset to let the ODBC driver choose the connection protocol
    # (needed for local named/default-instance connections over shared
    # memory, which is how this application connects to a local SQL Server
    # development instance). Set it to force a specific TCP port.
    mssql_port: int | None = Field(default=None)
    mssql_database: str = Field(default="")
    mssql_username: str = Field(default="")
    mssql_password: str = Field(default="")
    mssql_driver: str = Field(default="ODBC Driver 18 for SQL Server")
    mssql_encrypt: bool = Field(default=True)
    mssql_trust_server_certificate: bool = Field(default=False)

    @field_validator("mssql_port", mode="before")
    @classmethod
    def blank_port_means_unset(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    # --- MinIO ---
    minio_endpoint: str = Field(default="")
    minio_access_key: str = Field(default="")
    minio_secret_key: str = Field(default="")
    minio_bucket_name: str = Field(default="childcare-benefit")
    minio_secure: bool = Field(default=True)

    # --- Claim document uploads ---
    # Not specified in any project document — a standard, configurable
    # default (see DECISIONS_LOG.md item 22).
    max_upload_size_mb: int = Field(default=10)
    allowed_upload_extensions: str = Field(default="pdf,jpg,jpeg,png")

    @property
    def allowed_upload_extensions_set(self) -> set[str]:
        return {
            ext.strip().lower().lstrip(".")
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        }

    # --- Authentication (Version 1: Employee ID login) ---
    # No default is provided on purpose (see SECURITY.md — no secrets in
    # source code). Login and any protected endpoint fail with a clear,
    # safe error until this is set in the environment.
    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # --- Logging ---
    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Build the SQL Server SQLAlchemy connection URI.

        Returns an empty string when connection details are not configured,
        so the application can start (e.g. for the health endpoint) before a
        database has been provisioned for this environment.
        """
        if self.mssql_auth_mode == "sql":
            if not (self.mssql_server and self.mssql_database and self.mssql_username):
                return ""
            credentials = f"{self.mssql_username}:{self.mssql_password}"
        else:
            if not (self.mssql_server and self.mssql_database):
                return ""
            credentials = ""

        host = f"{self.mssql_server}:{self.mssql_port}" if self.mssql_port else self.mssql_server
        driver = self.mssql_driver.replace(" ", "+")
        encrypt = "yes" if self.mssql_encrypt else "no"
        trust_cert = "yes" if self.mssql_trust_server_certificate else "no"
        query = f"driver={driver}&Encrypt={encrypt}&TrustServerCertificate={trust_cert}"
        if self.mssql_auth_mode == "windows":
            query += "&trusted_connection=yes"

        return f"mssql+pyodbc://{credentials}@{host}/{self.mssql_database}?{query}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
