"""Payout monthly ledger and allocation — see PAYOUT_REQUIREMENTS.md.

Both tables are purely derived/disposable: fully deleted and regenerated
for a given EligibilityID every time app/services/payout_service.
recalculate_payout runs. Neither is ever individually edited, so there is
no UpdatedDate/UpdatedBy and no status column — see DECISIONS_LOG.md
items 44-49.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PayoutMonthlyLedger(Base):
    __tablename__ = "Childcare_PayoutMonthlyLedger"
    __table_args__ = (
        UniqueConstraint("EligibilityID", "PayoutMonth", name="UQ_PayoutLedger_Eligibility_Month"),
        Index("IX_PayoutLedger_EligibilityID", "EligibilityID"),
        Index("IX_PayoutLedger_MEmpID", "MEmpID"),
    )

    PayoutLedgerID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Plain indexed column, not a foreign key — see ChildMaster.MEmpID.
    MEmpID: Mapped[int]
    EmployeeID: Mapped[str]
    ChildID: Mapped[str] = mapped_column(ForeignKey("Childcare_ChildMaster.ChildID"))
    EligibilityID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_EligibilityMaster.EligibilityID")
    )
    FinancialYearID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_FinancialYearMaster.FinancialYearID")
    )
    FinancialYear: Mapped[str]
    PayoutMonth: Mapped[date] = mapped_column(Date)
    EntitlementAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    OpeningBalance: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    TotalAvailableAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    ClaimAllocatedAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    AdjustmentAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    ClosingBalance: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    CalculatedPayoutAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())


class PayoutAllocation(Base):
    __tablename__ = "Childcare_PayoutAllocation"
    __table_args__ = (
        Index("IX_PayoutAllocation_ClaimID", "ClaimID"),
        Index("IX_PayoutAllocation_EligibilityID", "EligibilityID"),
        Index("IX_PayoutAllocation_PayoutLedgerID", "PayoutLedgerID"),
    )

    PayoutAllocationID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ClaimID: Mapped[int] = mapped_column(ForeignKey("Childcare_ClaimMaster.ClaimID"))
    PayoutLedgerID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_PayoutMonthlyLedger.PayoutLedgerID")
    )
    # Plain indexed column, not a foreign key — see ChildMaster.MEmpID.
    MEmpID: Mapped[int]
    EmployeeID: Mapped[str]
    ChildID: Mapped[str]
    EligibilityID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_EligibilityMaster.EligibilityID")
    )
    FinancialYearID: Mapped[int]
    PayoutMonth: Mapped[date] = mapped_column(Date)
    AllocationSequence: Mapped[int]
    AllocatedAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
