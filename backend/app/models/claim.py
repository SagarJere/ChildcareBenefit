from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

DRAFT = "Draft"
SUBMITTED = "Submitted"
HR_REVIEW = "HRReview"
APPROVED = "Approved"
REJECTED = "Rejected"
SENT_BACK = "SentBack"


class ClaimMaster(Base):
    __tablename__ = "Childcare_ClaimMaster"
    __table_args__ = (
        Index("IX_ClaimMaster_MEmpID", "MEmpID"),
        Index("IX_ClaimMaster_ChildID", "ChildID"),
        Index("IX_ClaimMaster_ClaimStatus", "ClaimStatus"),
    )

    ClaimID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Plain indexed column, not a foreign key — see ChildMaster.MEmpID.
    MEmpID: Mapped[int]
    EmployeeID: Mapped[str]
    ChildID: Mapped[str] = mapped_column(ForeignKey("Childcare_ChildMaster.ChildID"))
    EligibilityID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_EligibilityMaster.EligibilityID")
    )
    InvoiceDate: Mapped[date] = mapped_column(Date)
    InvoiceNumber: Mapped[str]
    InvoiceAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    ClaimAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    # Descriptive fields only (user direction 2026-09-24) — they record
    # which institution provided the service and the period it covers,
    # validated against the child's age in months, but do not affect
    # which EligibilityID the claim posts against (still InvoiceDate) or
    # payout allocation (still HR approval time). Nullable since claims
    # created before this feature don't have them.
    InstitutionName: Mapped[str | None] = mapped_column(nullable=True)
    FromDate: Mapped[date | None] = mapped_column(Date, nullable=True)
    ToDate: Mapped[date | None] = mapped_column(Date, nullable=True)
    ClaimStatus: Mapped[str]
    Comments: Mapped[str | None] = mapped_column(nullable=True)
    SubmittedDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
    CreatedBy: Mapped[str]
    UpdatedDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    UpdatedBy: Mapped[str | None] = mapped_column(nullable=True)
