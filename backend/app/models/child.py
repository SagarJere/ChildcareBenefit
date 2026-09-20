from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ChildMaster(Base):
    __tablename__ = "Childcare_ChildMaster"
    __table_args__ = (
        UniqueConstraint("MEmpID", "ChildSequenceNo", name="UQ_ChildMaster_Employee_Sequence"),
        Index("IX_ChildMaster_MEmpID", "MEmpID"),
    )

    ChildID: Mapped[str] = mapped_column(primary_key=True)
    # Plain indexed column, not a foreign key: Master_Emp_BasicInfo has no
    # primary key or unique constraint to reference (see DECISIONS_LOG.md
    # item 14).
    MEmpID: Mapped[int]
    EmployeeID: Mapped[str]
    ChildSequenceNo: Mapped[int]
    ChildName: Mapped[str]
    ChildDOB: Mapped[date] = mapped_column(Date)
    IsActive: Mapped[bool] = mapped_column(default=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
    CreatedBy: Mapped[str]
    UpdatedDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    UpdatedBy: Mapped[str | None] = mapped_column(nullable=True)
