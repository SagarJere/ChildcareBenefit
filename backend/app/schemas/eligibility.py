from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.eligibility import EligibilityMaster


class EligibilityPreview(BaseModel):
    financial_year: str
    financial_year_start_date: date
    financial_year_end_date: date
    eligibility_start_date: date
    eligibility_end_date: date | None
    eligible_months: int
    monthly_benefit_amount: Decimal
    allotted_amount: Decimal


class EligibilityResponse(BaseModel):
    eligibility_id: int
    child_id: str
    financial_year: str
    eligibility_start_date: date
    eligibility_end_date: date | None
    eligible_months: int
    monthly_benefit_amount: Decimal
    allotted_amount: Decimal
    utilized_amount: Decimal
    approved_amount: Decimal
    in_progress_amount: Decimal
    remaining_amount: Decimal

    @classmethod
    def from_orm_model(cls, eligibility: EligibilityMaster) -> EligibilityResponse:
        return cls(
            eligibility_id=eligibility.EligibilityID,
            child_id=eligibility.ChildID,
            financial_year=eligibility.FinancialYear,
            eligibility_start_date=eligibility.EligibilityStartDate,
            eligibility_end_date=eligibility.EligibilityEndDate,
            eligible_months=eligibility.EligibleMonths,
            monthly_benefit_amount=eligibility.MonthlyBenefitAmount,
            allotted_amount=eligibility.AllottedAmount,
            utilized_amount=eligibility.UtilizedAmount,
            approved_amount=eligibility.ApprovedAmount,
            in_progress_amount=eligibility.InProgressAmount,
            remaining_amount=eligibility.RemainingAmount,
        )


class EmployeeEligibilityReportRow(BaseModel):
    eligibility_id: int
    child_id: str
    child_name: str
    child_dob: date
    financial_year: str
    eligible_months: int
    monthly_benefit_amount: Decimal
    allotted_amount: Decimal
    # Computed live from claim/approval-history data for display, the same
    # way as the HR Eligibility Utilization report — never read from
    # EligibilityMaster's own (never-updated) balance columns. See
    # DECISIONS_LOG.md items 32 and 41.
    utilized_amount: Decimal
    in_progress_amount: Decimal
    balance_amount: Decimal
    last_modified_date: datetime


class EmployeeEligibilityReportResponse(BaseModel):
    rows: list[EmployeeEligibilityReportRow]
