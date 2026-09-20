"""Read-only mapping onto the existing `Master_Emp_BasicInfo` table.

This table is owned outside this application (see
ChildcareBenefit_Codex_Documentation/CODEX_MASTER_INSTRUCTIONS.md §5) and is
never created, altered, or dropped by Alembic here. Column names/types and
nullability were verified directly against the real table on 2026-09-19 via
INFORMATION_SCHEMA — there is no `Gender` column, and no PK/unique
constraint currently exists on this table, so `EmployeeID` uniqueness is not
enforced at the database level.
"""
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MasterEmpBasicInfo(Base):
    __tablename__ = "Master_Emp_BasicInfo"

    # No physical primary key exists on this table; MEmpID is declared as
    # the ORM-level identity per CODEX_MASTER_INSTRUCTIONS.md §5 ("Use
    # MEmpID as the internal relationship key"). autoincrement=False is
    # required because MEmpID is verified NOT to be a SQL Server identity
    # column — without it, SQLAlchemy issues `SET IDENTITY_INSERT ON` for
    # any INSERT, which SQL Server rejects for a non-identity column.
    MEmpID: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    EmployeeID: Mapped[str | None] = mapped_column(nullable=True)
    FullName: Mapped[str | None] = mapped_column(nullable=True)
    MySingleID: Mapped[str | None] = mapped_column(nullable=True)
    Joindate: Mapped[datetime | None] = mapped_column(nullable=True)
    IsActive: Mapped[bool | None] = mapped_column(nullable=True)

    @property
    def is_active(self) -> bool:
        return self.IsActive is True
