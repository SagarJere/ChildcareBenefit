"""Shared SQLAlchemy declarative base.

All ORM models (added in later increments) must inherit from this base so
Alembic autogenerate can discover them via a single metadata object.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
