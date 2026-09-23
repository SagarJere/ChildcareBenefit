"""Pure eligibility calculation logic — no database access.

Kept dependency-free and side-effect-free so every business-rule scenario
in TESTING_STRATEGY.md (financial year, joining date, child DOB, six-year
limit, eligible months, the flat monthly amount) can be tested directly,
and so this is the single dedicated place eligibility math lives per
CODEX_MASTER_INSTRUCTIONS.md §8 ("must not be duplicated across multiple
endpoints").
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

MONTHLY_BENEFIT_AMOUNT = Decimal("14000")
SIX_YEAR_LIMIT_YEARS = 6
DOCUMENT_FREE_CHILD_MONTHS = 12
FIRST_YEAR_PAYOUT_CHILD_MONTHS = 13


@dataclass(frozen=True)
class FinancialYearWindow:
    label: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class EligibilityCalculation:
    financial_year: str
    financial_year_start_date: date
    financial_year_end_date: date
    eligibility_start_date: date
    eligibility_end_date: date | None
    eligible_months: int
    monthly_benefit_amount: Decimal
    allotted_amount: Decimal


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_years_clamped(d: date, years: int) -> date:
    """Add whole years to a date, clamping Feb 29 to Feb 28 if the target
    year is not a leap year (there is no business rule for this rare edge
    case, so a standard, unambiguous convention is used)."""
    target_year = d.year + years
    try:
        return date(target_year, d.month, d.day)
    except ValueError:
        return date(target_year, d.month, d.day - 1)


def _last_day_of_month(d: date) -> date:
    next_month_start = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return next_month_start - timedelta(days=1)


def _months_between_inclusive(start_month: date, end_month: date) -> int:
    return (end_month.year - start_month.year) * 12 + (end_month.month - start_month.month) + 1


def compute_financial_year(as_of: date) -> FinancialYearWindow:
    """Financial year runs April 1 through March 31."""
    start_year = as_of.year if as_of.month >= 4 else as_of.year - 1
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)
    label = f"{start_year}-{str(start_year + 1)[-2:]}"
    return FinancialYearWindow(label=label, start_date=start_date, end_date=end_date)


def calculate_eligibility(
    *, employee_join_date: date, child_dob: date, as_of: date
) -> EligibilityCalculation:
    """Calculate the current financial year's eligibility window for a child.

    Eligibility starts from the latest applicable month among the
    financial year start, the employee's joining month, and the child's
    birth month. It ends at the earlier of the financial year end and the
    calendar month containing the child's 6th birthday (inclusive).
    """
    fy = compute_financial_year(as_of)

    start_month = max(
        _month_start(fy.start_date),
        _month_start(employee_join_date),
        _month_start(child_dob),
    )

    six_year_cutoff_month = _month_start(_add_years_clamped(child_dob, SIX_YEAR_LIMIT_YEARS))
    end_month = min(_month_start(fy.end_date), six_year_cutoff_month)

    if end_month < start_month:
        return EligibilityCalculation(
            financial_year=fy.label,
            financial_year_start_date=fy.start_date,
            financial_year_end_date=fy.end_date,
            eligibility_start_date=start_month,
            eligibility_end_date=None,
            eligible_months=0,
            monthly_benefit_amount=MONTHLY_BENEFIT_AMOUNT,
            allotted_amount=Decimal("0"),
        )

    eligible_months = _months_between_inclusive(start_month, end_month)
    return EligibilityCalculation(
        financial_year=fy.label,
        financial_year_start_date=fy.start_date,
        financial_year_end_date=fy.end_date,
        eligibility_start_date=start_month,
        eligibility_end_date=_last_day_of_month(end_month),
        eligible_months=eligible_months,
        monthly_benefit_amount=MONTHLY_BENEFIT_AMOUNT,
        allotted_amount=Decimal(eligible_months) * MONTHLY_BENEFIT_AMOUNT,
    )


def next_financial_year_window(current_fy: FinancialYearWindow) -> FinancialYearWindow:
    """The financial year immediately following `current_fy`."""
    return compute_financial_year(current_fy.end_date + timedelta(days=1))


def next_financial_year_needed(*, child_dob: date, current_fy: FinancialYearWindow) -> bool:
    """Whether an eligibility record should also be created for the
    financial year immediately following `current_fy` (user direction
    2026-09-20; see DECISIONS_LOG.md item 43): eligibility should by
    default extend one financial year ahead, capped at the child's 72nd
    month (6th birthday/six-year limit) — if that cutoff already falls
    within `current_fy`, there is nothing left to allot next year, so no
    next-financial-year record is needed."""
    six_year_cutoff_month = _month_start(_add_years_clamped(child_dob, SIX_YEAR_LIMIT_YEARS))
    return six_year_cutoff_month > _month_start(current_fy.end_date)


def child_month_number(*, child_dob: date, invoice_date: date) -> int:
    """The child's age in whole months at the invoice date, counted from
    their date of birth (confirmed business decision — not from when
    benefit eligibility began; see DECISIONS_LOG.md item 17). The birth
    month itself is month 1.
    """
    dob_month = _month_start(child_dob)
    invoice_month = _month_start(invoice_date)
    return (invoice_month.year - dob_month.year) * 12 + (invoice_month.month - dob_month.month) + 1


def claim_requires_documents(*, child_dob: date, invoice_date: date) -> bool:
    """True from the child's 13th month onward (see BUSINESS_RULES.md)."""
    return child_month_number(child_dob=child_dob, invoice_date=invoice_date) > (
        DOCUMENT_FREE_CHILD_MONTHS
    )


def is_first_year_payout_month(*, child_dob: date, month: date) -> bool:
    """True for the child's first 13 months of life (month 1 = birth
    month) — the period that is paid automatically, with no employee
    claim, per the first-year-payout rule (user direction 2026-09-22).
    From month 14 onward, payout is driven by approved claims as before.

    A `month` before the child's own birth month is explicitly excluded
    (`child_month_number` would otherwise return zero or negative, which
    satisfies "<= 13" too) — there is no such thing as a first-year
    payout month before the child existed.
    """
    number = child_month_number(child_dob=child_dob, invoice_date=month)
    return 1 <= number <= FIRST_YEAR_PAYOUT_CHILD_MONTHS
