from datetime import date, datetime

from sqlalchemy import Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FinancialYearMaster(Base):
    __tablename__ = "Childcare_FinancialYearMaster"

    FinancialYearID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    FinancialYear: Mapped[str] = mapped_column(unique=True)
    StartDate: Mapped[date] = mapped_column(Date)
    EndDate: Mapped[date] = mapped_column(Date)
    IsActive: Mapped[bool] = mapped_column(default=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
