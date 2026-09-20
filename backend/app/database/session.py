"""SQL Server engine and session factory.

The engine is created lazily and only connects on first use, so the API can
start (and its health endpoint can respond) even before a SQL Server
instance/database has been provisioned for the current environment.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        database_uri = settings.sqlalchemy_database_uri
        if not database_uri:
            raise RuntimeError(
                "SQL Server connection is not configured. Set MSSQL_SERVER, "
                "MSSQL_DATABASE and MSSQL_USERNAME (and MSSQL_PASSWORD) "
                "environment variables."
            )
        _engine = create_engine(database_uri, pool_pre_ping=True, fast_executemany=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
