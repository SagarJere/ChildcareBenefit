from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ClaimSummaryRow(BaseModel):
    claim_id: int
    employee_id: str
    employee_name: str
    child_id: str
    child_name: str
    invoice_date: date
    invoice_number: str
    invoice_amount: Decimal
    claim_amount: Decimal
    institution_name: str | None
    from_date: date | None
    to_date: date | None
    claim_status: str
    submitted_date: datetime | None
    approved_date: datetime | None


class ClaimsSummaryTotals(BaseModel):
    total_claims: int
    count_by_status: dict[str, int]
    total_invoice_amount: Decimal
    total_approved_amount: Decimal


class ClaimsSummaryResponse(BaseModel):
    rows: list[ClaimSummaryRow]
    totals: ClaimsSummaryTotals


class EligibilityUtilizationRow(BaseModel):
    eligibility_id: int
    employee_id: str
    employee_name: str
    child_id: str
    child_name: str
    financial_year: str
    eligible_months: int
    monthly_benefit_amount: Decimal
    allotted_amount: Decimal
    # Computed live from claim/history data for display — see
    # DECISIONS_LOG.md item 32. Not read from EligibilityMaster's own
    # (never-updated) balance columns.
    in_progress_amount: Decimal
    approved_amount: Decimal
    # The child's first-13-months auto-paid total (Childcare_
    # PayoutMonthlyLedger) — shown as its own column so it's never just
    # an invisible gap between allotted_amount and remaining_after_
    # approved (user-caught 2026-09-24: "approved is showing 0, it
    # should have been 56k" for a child with only first-year payout and
    # no claims at all).
    first_year_payout_amount: Decimal
    remaining_after_approved: Decimal


class EligibilityUtilizationTotals(BaseModel):
    total_allotted_amount: Decimal
    total_in_progress_amount: Decimal
    total_approved_amount: Decimal
    total_first_year_payout_amount: Decimal


class EligibilityUtilizationResponse(BaseModel):
    rows: list[EligibilityUtilizationRow]
    totals: EligibilityUtilizationTotals


class HeadcountByFinancialYear(BaseModel):
    financial_year: str
    child_count: int


class HeadcountByAgeBracket(BaseModel):
    age_bracket: str
    child_count: int


class HeadcountResponse(BaseModel):
    total_employees_with_children: int
    total_children: int
    employees_with_one_child: int
    employees_with_two_children: int
    # Grouped by each child's original enrollment financial year — see
    # DECISIONS_LOG.md item 34 for why this isn't a "current status".
    by_financial_year: list[HeadcountByFinancialYear]
    by_age_bracket: list[HeadcountByAgeBracket]


class PayoutReportRow(BaseModel):
    """One Employee + Child + Financial Year, April-through-March — see
    PAYOUT_REQUIREMENTS.md §9's originally-proposed Childcare_
    PayoutSummary shape. Computed live from Childcare_PayoutMonthlyLedger
    (see DECISIONS_LOG.md item 50) rather than a separate stored summary
    table, the same "live report, not a stored aggregate" pattern already
    used for the other HR reports."""

    employee_id: str
    employee_name: str
    child_id: str
    child_name: str
    child_dob: date
    financial_year: str
    apr: Decimal
    may: Decimal
    jun: Decimal
    jul: Decimal
    aug: Decimal
    sep: Decimal
    oct: Decimal
    nov: Decimal
    dec: Decimal
    jan: Decimal
    feb: Decimal
    mar: Decimal
    total_payout: Decimal


class PayoutReportTotals(BaseModel):
    total_payout: Decimal


class PayoutReportResponse(BaseModel):
    rows: list[PayoutReportRow]
    totals: PayoutReportTotals
