from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.database.session import get_db
from app.dependencies.auth import get_current_employee
from app.repositories import employee_repository
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.employee import ActiveEmployeeOption, EmployeeProfile
from app.services import auth_service

router = APIRouter()


@router.get("/auth/active-employees", response_model=list[ActiveEmployeeOption])
def list_active_employees(db: Session = Depends(get_db)) -> list[ActiveEmployeeOption]:
    """Deliberately public (no auth) — feeds the login page's employee
    autocomplete, since a user has no token before logging in. This is a
    known, accepted tradeoff against the login endpoint's own
    no-enumeration design (see DECISIONS_LOG.md item 42): it returns the
    full active-employee roster (ID + name) to anyone who can reach this
    API, logged in or not."""
    return [
        ActiveEmployeeOption.from_orm_model(employee)
        for employee in employee_repository.get_all_active(db)
    ]


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return auth_service.login(db, payload.employee_id)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get("/me", response_model=EmployeeProfile)
def get_me(current_employee: EmployeeProfile = Depends(get_current_employee)) -> EmployeeProfile:
    return current_employee
