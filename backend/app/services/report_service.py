"""HR report business logic.

See DECISIONS_LOG.md items 31-34 for the scope decisions behind these
three reports (confirmed with the user, since almost none of this was
specified in the project documentation).
"""
import csv
import io
from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories import (
    child_repository,
    eligibility_repository,
    employee_repository,
    payout_repository,
    report_repository,
)
from app.schemas.eligibility import EmployeeEligibilityReportResponse, EmployeeEligibilityReportRow
from app.schemas.reports import (
    ClaimsSummaryResponse,
    ClaimsSummaryTotals,
    ClaimSummaryRow,
    EligibilityUtilizationResponse,
    EligibilityUtilizationRow,
    EligibilityUtilizationTotals,
    HeadcountByAgeBracket,
    HeadcountByFinancialYear,
    HeadcountResponse,
    PayoutReportResponse,
    PayoutReportRow,
    PayoutReportTotals,
)

_AGE_BRACKETS = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6+"]

_MONTH_FIELD_BY_NUMBER = {
    4: "apr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "aug",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dec",
    1: "jan",
    2: "feb",
    3: "mar",
}


def _age_bracket(dob: date, as_of: date) -> str:
    age_years = as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))
    if age_years >= 6:
        return "6+"
    return _AGE_BRACKETS[max(age_years, 0)]


def build_claims_summary(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    employee_id: str | None,
) -> ClaimsSummaryResponse:
    claims = report_repository.get_claims_for_report(
        db, date_from=date_from, date_to=date_to, status=status, employee_id=employee_id
    )

    child_names = {
        child.ChildID: child.ChildName for child in child_repository.get_all_active_children(db)
    }
    employee_names = employee_repository.get_names_by_employee_ids(
        db, [claim.EmployeeID for claim in claims]
    )

    eligibility_ids = [claim.EligibilityID for claim in claims]
    approved_totals = report_repository.get_approved_totals_by_eligibility(db, eligibility_ids)
    approved_dates = report_repository.get_approved_dates_by_claim(
        db, [claim.ClaimID for claim in claims]
    )

    rows = [
        ClaimSummaryRow(
            claim_id=claim.ClaimID,
            employee_id=claim.EmployeeID,
            employee_name=employee_names.get(claim.EmployeeID, claim.EmployeeID),
            child_id=claim.ChildID,
            child_name=child_names.get(claim.ChildID, claim.ChildID),
            invoice_date=claim.InvoiceDate,
            invoice_number=claim.InvoiceNumber,
            invoice_amount=claim.InvoiceAmount,
            claim_amount=claim.ClaimAmount,
            claim_status=claim.ClaimStatus,
            submitted_date=claim.SubmittedDate,
            approved_date=approved_dates.get(claim.ClaimID),
        )
        for claim in claims
    ]

    count_by_status = dict(Counter(claim.ClaimStatus for claim in claims))
    total_invoice_amount = sum((claim.InvoiceAmount for claim in claims), Decimal("0"))
    total_approved_amount = sum(
        (
            amount
            for claim, amount in (
                (claim, approved_totals.get(claim.EligibilityID)) for claim in claims
            )
            if claim.ClaimStatus == "Approved" and amount is not None
        ),
        Decimal("0"),
    )

    return ClaimsSummaryResponse(
        rows=rows,
        totals=ClaimsSummaryTotals(
            total_claims=len(claims),
            count_by_status=count_by_status,
            total_invoice_amount=total_invoice_amount,
            total_approved_amount=total_approved_amount,
        ),
    )


def build_eligibility_utilization(
    db: Session, *, financial_year: str | None, employee_id: str | None
) -> EligibilityUtilizationResponse:
    eligibility_rows = report_repository.get_all_eligibility(
        db, financial_year=financial_year, employee_id=employee_id
    )

    employee_names = employee_repository.get_names_by_employee_ids(
        db, [row.EmployeeID for row in eligibility_rows]
    )
    eligibility_ids = [row.EligibilityID for row in eligibility_rows]
    approved_totals = report_repository.get_approved_totals_by_eligibility(db, eligibility_ids)
    in_progress_totals = report_repository.get_in_progress_totals_by_eligibility(
        db, eligibility_ids
    )

    rows = []
    for row in eligibility_rows:
        approved = approved_totals.get(row.EligibilityID, Decimal("0"))
        in_progress = in_progress_totals.get(row.EligibilityID, Decimal("0"))
        rows.append(
            EligibilityUtilizationRow(
                eligibility_id=row.EligibilityID,
                employee_id=row.EmployeeID,
                employee_name=employee_names.get(row.EmployeeID, row.EmployeeID),
                child_id=row.ChildID,
                child_name=row.ChildName,
                financial_year=row.FinancialYear,
                eligible_months=row.EligibleMonths,
                monthly_benefit_amount=row.MonthlyBenefitAmount,
                allotted_amount=row.AllottedAmount,
                in_progress_amount=in_progress,
                approved_amount=approved,
                remaining_after_approved=row.AllottedAmount - approved,
            )
        )

    return EligibilityUtilizationResponse(
        rows=rows,
        totals=EligibilityUtilizationTotals(
            total_allotted_amount=sum((r.allotted_amount for r in rows), Decimal("0")),
            total_in_progress_amount=sum((r.in_progress_amount for r in rows), Decimal("0")),
            total_approved_amount=sum((r.approved_amount for r in rows), Decimal("0")),
        ),
    )


def build_employee_eligibility_report(
    db: Session, *, memp_id: int
) -> EmployeeEligibilityReportResponse:
    """The employee-facing, kid-wise, financial-year-wise eligibility
    report (user direction 2026-09-19, see DECISIONS_LOG.md item 41) —
    the same live-computed-from-claims approach as the HR Eligibility
    Utilization report (item 32), scoped to one employee's own children,
    plus a "last modified" column."""
    eligibility_rows = eligibility_repository.get_for_employee(db, memp_id)

    eligibility_ids = [row.EligibilityID for row in eligibility_rows]
    approved_totals = report_repository.get_approved_totals_by_eligibility(db, eligibility_ids)
    in_progress_totals = report_repository.get_in_progress_totals_by_eligibility(
        db, eligibility_ids
    )
    last_activity = report_repository.get_last_activity_by_eligibility(db, eligibility_ids)

    rows = []
    for row in eligibility_rows:
        utilized = approved_totals.get(row.EligibilityID, Decimal("0"))
        in_progress = in_progress_totals.get(row.EligibilityID, Decimal("0"))
        rows.append(
            EmployeeEligibilityReportRow(
                eligibility_id=row.EligibilityID,
                child_id=row.ChildID,
                child_name=row.ChildName,
                child_dob=row.ChildDOB,
                financial_year=row.FinancialYear,
                eligible_months=row.EligibleMonths,
                monthly_benefit_amount=row.MonthlyBenefitAmount,
                allotted_amount=row.AllottedAmount,
                utilized_amount=utilized,
                in_progress_amount=in_progress,
                balance_amount=row.AllottedAmount - utilized,
                last_modified_date=last_activity.get(row.EligibilityID, row.CreatedDate),
            )
        )

    return EmployeeEligibilityReportResponse(rows=rows)


def build_headcount(db: Session, *, as_of: date | None = None) -> HeadcountResponse:
    as_of = as_of or date.today()
    children = child_repository.get_all_active_children(db)

    children_per_employee = Counter(child.MEmpID for child in children)
    by_financial_year: Counter[str] = Counter()
    for row in report_repository.get_all_eligibility(db):
        by_financial_year[row.FinancialYear] += 1
    by_age_bracket = Counter(_age_bracket(child.ChildDOB, as_of) for child in children)

    return HeadcountResponse(
        total_employees_with_children=len(children_per_employee),
        total_children=len(children),
        employees_with_one_child=sum(1 for count in children_per_employee.values() if count == 1),
        employees_with_two_children=sum(
            1 for count in children_per_employee.values() if count >= 2
        ),
        by_financial_year=[
            HeadcountByFinancialYear(financial_year=fy, child_count=count)
            for fy, count in sorted(by_financial_year.items())
        ],
        by_age_bracket=[
            HeadcountByAgeBracket(age_bracket=bracket, child_count=by_age_bracket.get(bracket, 0))
            for bracket in _AGE_BRACKETS
        ],
    )


_LEDGER_FIELD_BY_SOURCE = {
    "claim": "ClaimAllocatedAmount",
    "first_year": "FirstYearPayoutAmount",
}


def build_payout_report(
    db: Session,
    *,
    financial_year: str | None,
    employee_id: str | None,
    child_id: str | None,
    source: str = "claim",
) -> PayoutReportResponse:
    """The HR payout report (user direction 2026-09-20; see
    DECISIONS_LOG.md item 50): one row per Employee + Child + Financial
    Year, April-through-March — the pivoted shape
    PAYOUT_REQUIREMENTS.md §9 originally proposed as a stored
    Childcare_PayoutSummary table, computed live from Childcare_
    PayoutMonthlyLedger instead (same "live report, not a stored
    aggregate" pattern as the other HR reports — see item 48's reasoning
    for why a dedicated summary table was deferred).

    `source` picks which of the ledger's two mutually-exclusive-per-month
    amounts to report on: `"claim"` (the original report — approved-claim
    payout, months 14+) or `"first_year"` (the child's first 13 months,
    auto-paid with no claim — see DECISIONS_LOG.md's first-year-payout
    Increment 4). A ledger row can exist from one source with nothing
    from the other (e.g. a fresh child's first-year rows before any claim
    is ever approved, or an older child's claim rows with no first-year
    months in range at all — see Increment 2's `_has_first_year_payout`
    guard) — groups with nothing to report for the requested `source` are
    excluded, the same "nothing-to-report cases aren't shown as all-zero
    rows" convention the report always had.
    """
    ledger_field = _LEDGER_FIELD_BY_SOURCE[source]
    ledger_rows = payout_repository.get_ledger_rows_for_report(
        db, financial_year=financial_year, employee_id=employee_id, child_id=child_id
    )
    if not ledger_rows:
        return PayoutReportResponse(rows=[], totals=PayoutReportTotals(total_payout=Decimal("0")))

    employee_names = employee_repository.get_names_by_employee_ids(
        db, [row.EmployeeID for row in ledger_rows]
    )
    children_by_id = {
        child.ChildID: child for child in child_repository.get_all_active_children(db)
    }

    grouped: dict[tuple[str, str, str], dict[str, Decimal]] = {}
    for row in ledger_rows:
        key = (row.EmployeeID, row.ChildID, row.FinancialYear)
        month_totals = grouped.setdefault(
            key, {field: Decimal("0") for field in _MONTH_FIELD_BY_NUMBER.values()}
        )
        field = _MONTH_FIELD_BY_NUMBER[row.PayoutMonth.month]
        month_totals[field] += getattr(row, ledger_field)

    rows = []
    for (emp_id, row_child_id, fy), month_totals in sorted(grouped.items()):
        total_payout = sum(month_totals.values(), Decimal("0"))
        if total_payout == 0:
            continue
        # ChildID is a foreign key on Childcare_PayoutMonthlyLedger, so the
        # row is guaranteed to exist.
        child = children_by_id.get(row_child_id)
        assert child is not None
        rows.append(
            PayoutReportRow(
                employee_id=emp_id,
                employee_name=employee_names.get(emp_id, emp_id),
                child_id=row_child_id,
                child_name=child.ChildName,
                child_dob=child.ChildDOB,
                financial_year=fy,
                total_payout=total_payout,
                **month_totals,
            )
        )

    return PayoutReportResponse(
        rows=rows,
        totals=PayoutReportTotals(
            total_payout=sum((row.total_payout for row in rows), Decimal("0"))
        ),
    )


def rows_to_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
