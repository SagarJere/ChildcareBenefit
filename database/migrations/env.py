"""Alembic environment configuration.

The database connection string is built from environment variables via the
application's Settings object rather than being hardcoded in alembic.ini, so
migrations always target the same database as the running application.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the backend "app" package importable when Alembic is invoked with
# --config backend/alembic.ini from the repository root or from backend/.
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.database.base import Base  # noqa: E402

# Import model modules here as they are added in later increments so that
# Base.metadata is populated for autogenerate support.
from app.models import (  # noqa: E402,F401
    child,
    claim,
    claim_approval_history,
    claim_attachment,
    eligibility,
    financial_year,
    hr_approver,
    payout_settings,
    payout_settings_history,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    settings = get_settings()
    url = settings.sqlalchemy_database_uri
    if not url:
        raise RuntimeError(
            "SQL Server connection is not configured. Set MSSQL_SERVER, "
            "MSSQL_DATABASE and MSSQL_USERNAME (and MSSQL_PASSWORD) "
            "environment variables before running migrations."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
