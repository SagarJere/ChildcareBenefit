from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.errors import (
    AttachmentNotFoundError,
    ChildNotFoundError,
    ClaimNotEditableError,
    ClaimNotFoundError,
    ClaimsBlockedError,
    DuplicateInvoiceError,
    FileTooLargeError,
    FinancialYearNotOpenError,
    FirstYearPayoutPeriodError,
    InvalidServicePeriodError,
    InvalidUploadError,
    NoEligibilityForPeriodError,
)
from app.database.session import get_db
from app.dependencies.auth import get_current_employee
from app.models.claim_attachment import PAYMENT_PROOF, RECEIPT_INVOICE
from app.schemas.attachment import AttachmentResponse
from app.schemas.claim import ClaimCreateRequest, ClaimResponse, ClaimUpdateRequest
from app.schemas.employee import EmployeeProfile
from app.services import claim_service
from app.services.storage.minio_client import MinioNotConfiguredError

router = APIRouter()

_VALID_ATTACHMENT_TYPES = {RECEIPT_INVOICE, PAYMENT_PROOF}


@router.post("/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    payload: ClaimCreateRequest,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    try:
        return claim_service.create_claim(db, current_employee, payload)
    except ChildNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FirstYearPayoutPeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NoEligibilityForPeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidServicePeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DuplicateInvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ClaimsBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FinancialYearNotOpenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/claims", response_model=list[ClaimResponse])
def list_claims(
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[ClaimResponse]:
    return claim_service.list_claims(db, current_employee)


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    try:
        return claim_service.get_claim(db, current_employee, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/claims/{claim_id}", response_model=ClaimResponse)
def update_claim(
    claim_id: int,
    payload: ClaimUpdateRequest,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    try:
        return claim_service.update_claim(db, current_employee, claim_id, payload)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotEditableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except FirstYearPayoutPeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NoEligibilityForPeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidServicePeriodError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DuplicateInvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except FinancialYearNotOpenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/submit", response_model=ClaimResponse)
def submit_claim(
    claim_id: int,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    try:
        return claim_service.submit_claim(db, current_employee, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotEditableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ClaimsBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.delete("/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: int,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    try:
        claim_service.delete_claim(db, current_employee, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotEditableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/claims/{claim_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    claim_id: int,
    attachment_type: str = Form(...),
    file: UploadFile = File(...),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    if attachment_type not in _VALID_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"attachment_type must be one of {sorted(_VALID_ATTACHMENT_TYPES)}.",
        )

    try:
        return claim_service.upload_attachment(
            db,
            current_employee,
            claim_id,
            attachment_type,
            filename=file.filename or "upload",
            content_type=file.content_type,
            file_stream=file.file,
        )
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClaimNotEditableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc
    except MinioNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is not configured.",
        ) from exc


@router.get("/claims/{claim_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(
    claim_id: int,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[AttachmentResponse]:
    try:
        return claim_service.list_attachments(db, current_employee, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/claims/{claim_id}/attachments/{attachment_id}/download")
def download_attachment(
    claim_id: int,
    attachment_id: int,
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        url = claim_service.get_attachment_download_url(
            db, current_employee, claim_id, attachment_id
        )
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
