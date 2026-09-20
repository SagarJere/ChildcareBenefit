from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import TokenError, decode_access_token
from app.database.session import get_db
from app.repositories import hr_approver_repository
from app.schemas.employee import EmployeeProfile
from app.services import auth_service

# auto_error=False so a missing/malformed Authorization header is handled
# below and reported as 401 (unauthenticated), matching
# ERROR_HANDLING_AND_LOGGING.md — HTTPBearer's own auto_error path would
# otherwise return 403 for this case, which is inconsistent with the rest
# of this API.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_employee(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> EmployeeProfile:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        ) from exc

    employee_id = payload.get("sub")
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    try:
        return auth_service.get_current_employee_profile(db, employee_id)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        ) from exc


def get_current_hr_approver(
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeProfile:
    """Requires the authenticated employee to also be a recognized, active
    HR approver (Childcare_HRApprovers) — a separate, additive check on
    top of ordinary employee authentication. Per CODEX_MASTER_
    INSTRUCTIONS.md §11, this is enforced here in the backend, not by
    hiding controls in the frontend."""
    if not hr_approver_repository.is_active_hr_approver(db, current_employee.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access HR functions.",
        )
    return current_employee
