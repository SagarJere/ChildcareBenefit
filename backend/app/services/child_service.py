"""Child management business logic.

Adding a child is implemented as the single atomic operation required by
CODEX_MASTER_INSTRUCTIONS.md §8: validate → generate ChildID → create the
child → calculate eligibility → create the eligibility record — all in one
database transaction (the request-scoped session commits once, at the very
end, only if every step succeeds; see app/database/session.py's get_db).
"""
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    ChildNotFoundError,
    DuplicateChildError,
    MaxChildrenExceededError,
    MissingJoinDateError,
)
from app.repositories import child_repository, eligibility_repository, financial_year_repository
from app.repositories.child_repository import MAX_CHILDREN_PER_EMPLOYEE
from app.schemas.child import ChildResponse
from app.schemas.eligibility import EligibilityPreview, EligibilityResponse
from app.schemas.employee import EmployeeProfile
from app.services import eligibility_balance_service, eligibility_calculator, payout_service


def _has_first_year_payout(
    calculation: eligibility_calculator.EligibilityCalculation, child_dob: date
) -> bool:
    """Whether this eligibility window contains any of the child's first
    13 months of life. Since child age only increases with calendar time,
    first-year months are always a *prefix* of the window (see
    payout_calculator.py) — so checking just the first month is enough.
    Guards the payout-ledger-creation call in add_child below, so a
    window with nothing to auto-pay (and no claims yet either) doesn't
    get pointless all-zero ledger rows — see DECISIONS_LOG.md's
    first-year-payout Increment 2 note."""
    if calculation.eligibility_end_date is None:
        return False
    return eligibility_calculator.is_first_year_payout_month(
        child_dob=child_dob, month=calculation.eligibility_start_date
    )


def _require_join_date(employee: EmployeeProfile) -> date:
    if employee.join_date is None:
        raise MissingJoinDateError(
            "Employee join date is not on file. Please contact HR before adding a child."
        )
    # employee.join_date is a datetime (the underlying column is DATETIME);
    # the eligibility calculator only cares about the calendar date.
    return employee.join_date.date()


def preview_eligibility(
    db: Session, employee: EmployeeProfile, child_dob: date
) -> EligibilityPreview:
    join_date = _require_join_date(employee)

    existing_children = child_repository.get_active_children(db, employee.memp_id)
    if len(existing_children) >= MAX_CHILDREN_PER_EMPLOYEE:
        raise MaxChildrenExceededError(
            f"Employee already has the maximum of {MAX_CHILDREN_PER_EMPLOYEE} children."
        )

    calculation = eligibility_calculator.calculate_eligibility(
        employee_join_date=join_date, child_dob=child_dob, as_of=date.today()
    )
    return EligibilityPreview(
        financial_year=calculation.financial_year,
        financial_year_start_date=calculation.financial_year_start_date,
        financial_year_end_date=calculation.financial_year_end_date,
        eligibility_start_date=calculation.eligibility_start_date,
        eligibility_end_date=calculation.eligibility_end_date,
        eligible_months=calculation.eligible_months,
        monthly_benefit_amount=calculation.monthly_benefit_amount,
        allotted_amount=calculation.allotted_amount,
    )


def add_child(
    db: Session, employee: EmployeeProfile, child_name: str, child_dob: date
) -> ChildResponse:
    join_date = _require_join_date(employee)

    existing_children = child_repository.get_active_children(db, employee.memp_id)

    # Guards against a duplicate submission — e.g. a slow response (a free
    # hosting tier's cold start can take 30-60s) makes the first attempt
    # look hung, the user resubmits, and both silently succeed as two
    # separate children with the same name/DOB. Case-insensitive since a
    # retyped name may differ only in casing.
    normalized_name = child_name.strip().casefold()
    if any(
        existing.ChildName.strip().casefold() == normalized_name
        and existing.ChildDOB == child_dob
        for existing in existing_children
    ):
        raise DuplicateChildError(
            f"A child named {child_name!r} with this date of birth is already on record."
        )

    if len(existing_children) >= MAX_CHILDREN_PER_EMPLOYEE:
        raise MaxChildrenExceededError(
            f"Employee already has the maximum of {MAX_CHILDREN_PER_EMPLOYEE} children."
        )

    sequence_no = child_repository.next_sequence_number(existing_children)
    child_id = f"{employee.employee_id}_{sequence_no}"

    calculation = eligibility_calculator.calculate_eligibility(
        employee_join_date=join_date, child_dob=child_dob, as_of=date.today()
    )
    fy_window = eligibility_calculator.compute_financial_year(date.today())
    financial_year_row = financial_year_repository.get_or_create(db, fy_window)

    try:
        # A SAVEPOINT, not the outer transaction: if a genuinely
        # concurrent request for this same employee won the race and
        # already inserted a child with this same name+DOB (the
        # UQ_ChildMaster_Employee_Name_DOB constraint), only this insert
        # attempt should be undone — the check above already catches the
        # common (non-concurrent) case; this is the narrower backstop for
        # a true race between two in-flight requests.
        with db.begin_nested():
            child = child_repository.create_child(
                db,
                child_id=child_id,
                memp_id=employee.memp_id,
                employee_id=employee.employee_id,
                sequence_no=sequence_no,
                child_name=child_name,
                child_dob=child_dob,
                created_by=employee.employee_id,
            )
    except IntegrityError as exc:
        raise DuplicateChildError(
            f"A child named {child_name!r} with this date of birth may already be on "
            "record, or another request for this employee is still being processed — "
            "please check My Children before trying again."
        ) from exc
    added_date = date.today()
    eligibility = eligibility_repository.create_eligibility(
        db,
        memp_id=employee.memp_id,
        employee_id=employee.employee_id,
        child_id=child_id,
        child_name=child_name,
        child_dob=child_dob,
        financial_year_id=financial_year_row.FinancialYearID,
        calculation=calculation,
        first_year_payout_as_of_date=added_date,
    )
    # Populates the payout ledger immediately when this window includes
    # any first-year-payout months — with no claims yet, this naturally
    # comes out as first-year-only rows (user direction 2026-09-22/23;
    # see app/services/payout_calculator.py). Skipped otherwise so a
    # child with nothing to auto-pay doesn't get pointless all-zero
    # ledger rows before any claim exists.
    if _has_first_year_payout(calculation, child_dob):
        payout_service.recalculate_payout(db, eligibility.EligibilityID)
        # Without this, UtilizedAmount/RemainingAmount would stay at
        # their initial (no-payout-yet) defaults despite real money
        # already having been auto-paid — see DECISIONS_LOG.md's
        # first-year-payout follow-up.
        eligibility_balance_service.sync_balance(db, eligibility.EligibilityID)

    # By default, eligibility also extends one financial year ahead,
    # capped at the child's 72nd month/6th birthday — see
    # DECISIONS_LOG.md item 43. Skipped when the six-year cutoff already
    # falls within the current financial year, since next year's record
    # would be zero anyway. This also already covers every case where the
    # child's first-13-months window itself spans two financial years,
    # since that window is always shorter than the six-year one.
    if eligibility_calculator.next_financial_year_needed(child_dob=child_dob, current_fy=fy_window):
        next_fy_window = eligibility_calculator.next_financial_year_window(fy_window)
        next_calculation = eligibility_calculator.calculate_eligibility(
            employee_join_date=join_date, child_dob=child_dob, as_of=next_fy_window.start_date
        )
        next_financial_year_row = financial_year_repository.get_or_create(db, next_fy_window)
        next_eligibility = eligibility_repository.create_eligibility(
            db,
            memp_id=employee.memp_id,
            employee_id=employee.employee_id,
            child_id=child_id,
            child_name=child_name,
            child_dob=child_dob,
            financial_year_id=next_financial_year_row.FinancialYearID,
            calculation=next_calculation,
            first_year_payout_as_of_date=added_date,
        )
        if _has_first_year_payout(next_calculation, child_dob):
            payout_service.recalculate_payout(db, next_eligibility.EligibilityID)
            eligibility_balance_service.sync_balance(db, next_eligibility.EligibilityID)

    return ChildResponse.from_orm_model(child, EligibilityResponse.from_orm_model(eligibility))


def list_children(db: Session, employee: EmployeeProfile) -> list[ChildResponse]:
    children = child_repository.get_active_children(db, employee.memp_id)
    fy_window = eligibility_calculator.compute_financial_year(date.today())
    eligibility_by_child = eligibility_repository.get_current_for_children(
        db, employee.memp_id, fy_window.label
    )

    return [
        ChildResponse.from_orm_model(
            child,
            EligibilityResponse.from_orm_model(eligibility_by_child[child.ChildID])
            if child.ChildID in eligibility_by_child
            else None,
        )
        for child in children
    ]


def get_child(db: Session, employee: EmployeeProfile, child_id: str) -> ChildResponse:
    child = child_repository.get_child_for_employee(db, employee.memp_id, child_id)
    if child is None:
        raise ChildNotFoundError(f"No child {child_id} found for this employee.")

    fy_window = eligibility_calculator.compute_financial_year(date.today())
    eligibility_rows = eligibility_repository.get_for_child(
        db, employee.memp_id, child_id, fy_window.label
    )
    eligibility = eligibility_rows[0] if eligibility_rows else None

    return ChildResponse.from_orm_model(
        child, EligibilityResponse.from_orm_model(eligibility) if eligibility else None
    )
