from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EligibilityMaster(Base):
    __tablename__ = "Childcare_EligibilityMaster"
    __table_args__ = (
        UniqueConstraint(
            "MEmpID", "ChildID", "FinancialYearID", name="UQ_Eligibility_Employee_Child_FY"
        ),
        Index("IX_EligibilityMaster_MEmpID", "MEmpID"),
        Index("IX_EligibilityMaster_ChildID", "ChildID"),
    )

    EligibilityID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Plain indexed column, not a foreign key — see ChildMaster.MEmpID.
    MEmpID: Mapped[int]
    EmployeeID: Mapped[str]
    ChildID: Mapped[str] = mapped_column(ForeignKey("Childcare_ChildMaster.ChildID"))
    ChildName: Mapped[str]
    ChildDOB: Mapped[date] = mapped_column(Date)
    FinancialYearID: Mapped[int] = mapped_column(
        ForeignKey("Childcare_FinancialYearMaster.FinancialYearID")
    )
    FinancialYear: Mapped[str]
    EligibilityStartDate: Mapped[date] = mapped_column(Date)
    EligibilityEndDate: Mapped[date | None] = mapped_column(Date, nullable=True)
    EligibleMonths: Mapped[int]
    MonthlyBenefitAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    AllottedAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    UtilizedAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    ApprovedAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    InProgressAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    RemainingAmount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2))
    IsActive: Mapped[bool] = mapped_column(default=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
    UpdatedDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
