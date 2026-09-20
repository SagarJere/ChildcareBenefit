from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.errors import (
    AttachmentNotFoundError,
    ClaimNotFoundError,
    ClaimNotReviewableError,
    InvalidApprovedAmountError,
)
from app.database.session import get_db
from app.dependencies.auth import get_current_hr_approver
from app.schemas.attachment import AttachmentResponse
from app.schemas.employee import EmployeeProfile
from app.schemas.hr import (
    ApproveRequest,
    HRClaimDetail,
    HRClaimSummary,
    RejectRequest,
    SendBackRequest,
)
from app.services import hr_service
from app.services.storage.minio_client import MinioNotConfiguredError

router = APIRouter()


@router.get("/hr/claims", response_model=list[HRClaimSummary])
def list_claims(
    status_filter: str | None = Query(default=None, alias="status"),
    employee_id: str | None = None,
    child_id: str | None = None,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[HRClaimSummary]:
    return hr_service.list_claims(db, status_filter, employee_id=employee_id, child_id=child_id)


@router.get("/hr/claims/{claim_id}", response_model=HRClaimDetail)
def get_claim(
    claim_id: int,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> HRClaimDetail:
    try:
        return hr_service.get_claim_detail(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/hr/claims/{claim_id}/approve", response_model=HRClaimDetail)
def approve_claim(
    claim_id: int,
    payload: ApproveRequest,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> HRClaimDetail:
    try:
        return hr_service.approve_claim(db, current_hr_employee.employee_id, claim_id, payload)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotReviewableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidApprovedAmountError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/hr/claims/{claim_id}/reject", response_model=HRClaimDetail)
def reject_claim(
    claim_id: int,
    payload: RejectRequest,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> HRClaimDetail:
    try:
        return hr_service.reject_claim(db, current_hr_employee.employee_id, claim_id, payload)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotReviewableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/hr/claims/{claim_id}/send-back", response_model=HRClaimDetail)
def send_back_claim(
    claim_id: int,
    payload: SendBackRequest,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> HRClaimDetail:
    try:
        return hr_service.send_back_claim(db, current_hr_employee.employee_id, claim_id, payload)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotReviewableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/hr/claims/{claim_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(
    claim_id: int,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[AttachmentResponse]:
    try:
        return hr_service.list_attachments(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/hr/claims/{claim_id}/attachments/{attachment_id}/download")
def download_attachment(
    claim_id: int,
    attachment_id: int,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        url = hr_service.get_attachment_download_url(db, claim_id, attachment_id)
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MinioNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is not configured.",
        ) from exc
