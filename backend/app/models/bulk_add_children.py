from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

CREATED = "Created"
FAILED = "Failed"


class BulkAddChildrenBatch(Base):
    """One row per HR bulk-add-children *commit* attempt (user direction
    2026-09-26) — recorded so a later dispute ("I uploaded 2, only 1 was
    added") can be settled by pointing at exactly what happened and why.
    Only real commit attempts are recorded here, never preview calls,
    since preview never actually persists anything (see
    child_bulk_service.py) and logging it would clutter this history
    with dry runs that never really happened."""

    __tablename__ = "Childcare_BulkAddChildrenBatch"
    __table_args__ = (
        Index("IX_BulkAddChildrenBatch_UploadedBy_UploadedDate", "UploadedBy", "UploadedDate"),
    )

    BulkUploadID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    UploadedBy: Mapped[str]
    UploadedFileName: Mapped[str | None] = mapped_column(nullable=True)
    TotalRows: Mapped[int] = mapped_column(Integer)
    SucceededCount: Mapped[int] = mapped_column(Integer)
    FailedCount: Mapped[int] = mapped_column(Integer)
    UploadedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())


class BulkAddChildrenRow(Base):
    """One row per CSV row processed within a batch — see
    BulkAddChildrenBatch's own comment. ChildDOBRaw is kept as the
    literal text from the file, not a date column, so a row that failed
    to parse at all is still fully recorded and "what did HR actually
    type" is never in question."""

    __tablename__ = "Childcare_BulkAddChildrenRow"
    __table_args__ = (
        Index("IX_BulkAddChildrenRow_BulkUploadID", "BulkUploadID"),
        Index("IX_BulkAddChildrenRow_EmployeeID", "EmployeeID"),
    )

    BulkUploadRowID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    BulkUploadID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_BulkAddChildrenBatch.BulkUploadID")
    )
    RowNumber: Mapped[int] = mapped_column(Integer)
    EmployeeID: Mapped[str]
    ChildName: Mapped[str]
    ChildDOBRaw: Mapped[str]
    Status: Mapped[str]
    Message: Mapped[str | None] = mapped_column(nullable=True)
    ChildID: Mapped[str | None] = mapped_column(
        ForeignKey("Childcare_ChildMaster.ChildID"), nullable=True
    )
