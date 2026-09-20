from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import ChildNotFoundError, MaxChildrenExceededError, MissingJoinDateError
from app.database.session import get_db
from app.dependencies.auth import get_current_employee
from app.schemas.child import ChildCreateRequest, ChildEligibilityPreviewRequest, ChildResponse
from app.schemas.eligibility import EligibilityPreview
from app.schemas.employee import EmployeeProfile
from app.services import child_service

router = APIRouter()


@router.post("/children/preview-eligibility", response_model=EligibilityPreview)
def preview_eligibility(
    payload: ChildEligibilityPreviewRequest,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EligibilityPreview:
    try:
        return child_service.preview_eligibility(db, current_employee, payload.child_dob)
    except MissingJoinDateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MaxChildrenExceededError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/children", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
def create_child(
    payload: ChildCreateRequest,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ChildResponse:
    try:
        return child_service.add_child(
            db, current_employee, payload.child_name, payload.child_dob
        )
    except MissingJoinDateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MaxChildrenExceededError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/children", response_model=list[ChildResponse])
def list_children(
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[ChildResponse]:
    return child_service.list_children(db, current_employee)


@router.get("/children/{child_id}", response_model=ChildResponse)
def get_child(
    child_id: str,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ChildResponse:
    try:
        return child_service.get_child(db, current_employee, child_id)
    except ChildNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
