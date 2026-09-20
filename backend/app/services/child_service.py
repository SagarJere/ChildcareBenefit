"""Child management business logic.

Adding a child is implemented as the single atomic operation required by
CODEX_MASTER_INSTRUCTIONS.md §8: validate → generate ChildID → create the
child → calculate eligibility → create the eligibility record — all in one
database transaction (the request-scoped session commits once, at the very
end, only if every step succeeds; see app/database/session.py's get_db).
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import ChildNotFoundError, MaxChildrenExceededError, MissingJoinDateError
from app.repositories import child_repository, eligibility_repository, financial_year_repository
from app.repositories.child_repository import MAX_CHILDREN_PER_EMPLOYEE
from app.schemas.child import ChildResponse
from app.schemas.eligibility import EligibilityPreview, EligibilityResponse
from app.schemas.employee import EmployeeProfile
from app.services import eligibility_calculator


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
    eligibility = eligibility_repository.create_eligibility(
        db,
        memp_id=employee.memp_id,
        employee_id=employee.employee_id,
        child_id=child_id,
        child_name=child_name,
        child_dob=child_dob,
        financial_year_id=financial_year_row.FinancialYearID,
        calculation=calculation,
    )

    # By default, eligibility also extends one financial year ahead,
    # capped at the child's 72nd month/6th birthday — see
    # DECISIONS_LOG.md item 43. Skipped when the six-year cutoff already
    # falls within the current financial year, since next year's record
    # would be zero anyway.
    if eligibility_calculator.next_financial_year_needed(child_dob=child_dob, current_fy=fy_window):
        next_fy_window = eligibility_calculator.next_financial_year_window(fy_window)
        next_calculation = eligibility_calculator.calculate_eligibility(
            employee_join_date=join_date, child_dob=child_dob, as_of=next_fy_window.start_date
        )
        next_financial_year_row = financial_year_repository.get_or_create(db, next_fy_window)
        eligibility_repository.create_eligibility(
            db,
            memp_id=employee.memp_id,
            employee_id=employee.employee_id,
            child_id=child_id,
            child_name=child_name,
            child_dob=child_dob,
            financial_year_id=next_financial_year_row.FinancialYearID,
            calculation=next_calculation,
        )

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
