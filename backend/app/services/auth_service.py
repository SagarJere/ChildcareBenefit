"""Employee Login business logic (Version 1: Employee ID only).

Sequence per CODEX_MASTER_INSTRUCTIONS.md §6:
1. Receive Employee ID.
2. Query Master_Emp_BasicInfo.
3. Verify employee exists.
4. Verify employee is active.
5. Return employee details through the defined authentication/session
   boundary (a signed access token, in this implementation).
"""
import logging

from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import create_access_token
from app.models.employee import MasterEmpBasicInfo
from app.repositories import employee_repository, hr_approver_repository
from app.schemas.auth import LoginResponse
from app.schemas.employee import EmployeeProfile

logger = logging.getLogger(__name__)


def _require_active_employee(db: Session, employee_id: str) -> MasterEmpBasicInfo:
    employee = employee_repository.get_by_employee_id(db, employee_id)

    if employee is None:
        logger.info("Login failed: no employee found for the supplied Employee ID.")
        raise AuthenticationError("Employee ID not found or not active.")

    if not employee.is_active:
        logger.info(
            "Login failed: employee MEmpID=%s is not active.", employee.MEmpID
        )
        raise AuthenticationError("Employee ID not found or not active.")

    return employee


def login(db: Session, employee_id: str) -> LoginResponse:
    employee = _require_active_employee(db, employee_id)

    # employee_id (the validated input) is used rather than employee.EmployeeID:
    # the repository lookup guarantees they match, but the column is nullable
    # on the underlying table so its static type is `str | None`.
    token = create_access_token(employee_id=employee_id, memp_id=employee.MEmpID)

    return LoginResponse(
        access_token=token,
        employee=EmployeeProfile.from_orm_model(
            employee, is_hr_approver=hr_approver_repository.is_active_hr_approver(db, employee_id)
        ),
    )


def get_current_employee_profile(db: Session, employee_id: str) -> EmployeeProfile:
    """Re-validates the employee behind an already-authenticated request.

    Always re-reads from the database rather than trusting the token's
    claims for anything beyond identity, so a token issued while an
    employee was active stops working the moment they are deactivated.
    """
    employee = _require_active_employee(db, employee_id)
    return EmployeeProfile.from_orm_model(
        employee, is_hr_approver=hr_approver_repository.is_active_hr_approver(db, employee_id)
    )
