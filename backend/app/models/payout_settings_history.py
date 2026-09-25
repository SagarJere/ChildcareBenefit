from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PayoutSettingsHistory(Base):
    """One row per actual change to Childcare_PayoutSettings (user
    direction 2026-09-25) — mirrors Childcare_ClaimApprovalHistory's
    before/after shape. Written only when a PUT to /hr/payout-settings
    actually changes something (see payout_settings_service.
    update_settings), not on every save attempt."""

    __tablename__ = "Childcare_PayoutSettingsHistory"
    __table_args__ = (Index("IX_PayoutSettingsHistory_ChangedDate", "ChangedDate"),)

    PayoutSettingsHistoryID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ChangedBy: Mapped[str]
    PreviousSubmissionCutoffDay: Mapped[int] = mapped_column(Integer)
    NewSubmissionCutoffDay: Mapped[int] = mapped_column(Integer)
    PreviousClaimsBlocked: Mapped[bool] = mapped_column(Boolean)
    NewClaimsBlocked: Mapped[bool] = mapped_column(Boolean)
    # Denormalized labels, not IDs — every row here is a permanent
    # snapshot of what changed, and a label is directly displayable with
    # no join needed (see PayoutSettings.OpenFinancialYear).
    PreviousOpenFinancialYear: Mapped[str | None] = mapped_column(nullable=True)
    NewOpenFinancialYear: Mapped[str | None] = mapped_column(nullable=True)
    PreviousForceSameMonthPayout: Mapped[bool] = mapped_column(Boolean)
    NewForceSameMonthPayout: Mapped[bool] = mapped_column(Boolean)
    ChangedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
