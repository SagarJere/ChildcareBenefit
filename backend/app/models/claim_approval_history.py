from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

APPROVED = "Approved"
REJECTED = "Rejected"
SENT_BACK = "SentBack"


class ClaimApprovalHistory(Base):
    __tablename__ = "Childcare_ClaimApprovalHistory"
    __table_args__ = (Index("IX_ApprovalHistory_ClaimID", "ClaimID"),)

    ApprovalHistoryID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ClaimID: Mapped[int] = mapped_column(ForeignKey("Childcare_ClaimMaster.ClaimID"))
    ActionBy: Mapped[str]
    Action: Mapped[str]
    PreviousStatus: Mapped[str]
    NewStatus: Mapped[str]
    ApprovedAmount: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    Remarks: Mapped[str | None] = mapped_column(nullable=True)
    ActionDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
