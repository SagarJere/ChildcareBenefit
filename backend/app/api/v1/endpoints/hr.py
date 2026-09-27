from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.errors import (
    AttachmentNotFoundError,
    BulkFileFormatError,
    BulkRowLimitExceededError,
    ClaimNotFoundError,
    ClaimNotReviewableError,
    DuplicateChildError,
    EmployeeNotFoundError,
    InvalidApprovedAmountError,
    MaxChildrenExceededError,
    MissingJoinDateError,
)
from app.database.session import get_db
from app.dependencies.auth import get_current_hr_approver
from app.repositories import bulk_add_children_repository
from app.schemas.attachment import AttachmentResponse
from app.schemas.child import ChildResponse, HRChildCreateRequest
from app.schemas.child_bulk import (
    BulkAddChildrenResponse,
    BulkChildRowResult,
    BulkUploadBatchDetail,
    BulkUploadBatchSummary,
)
from app.schemas.employee import EmployeeProfile
from app.schemas.hr import (
    ApproveRequest,
    HRClaimDetail,
    HRClaimSummary,
    RejectRequest,
    SendBackRequest,
)
from app.services import child_bulk_service, child_service, hr_service
from app.services.storage.minio_client import MinioNotConfiguredError

router = APIRouter()


@router.post("/hr/children", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
def add_child(
    payload: HRChildCreateRequest,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> ChildResponse:
    try:
        return child_service.add_child_for_employee(
            db,
            target_employee_id=payload.employee_id,
            child_name=payload.child_name,
            child_dob=payload.child_dob,
            added_by=current_hr_employee.employee_id,
        )
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MissingJoinDateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MaxChildrenExceededError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DuplicateChildError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/hr/children/bulk/preview", response_model=BulkAddChildrenResponse)
def preview_bulk_add_children(
    file: UploadFile = File(...),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> BulkAddChildrenResponse:
    """Runs the whole file for real against a SAVEPOINT that's always
    rolled back — see child_bulk_service's own comment — so nothing here
    persists; the same file is re-uploaded to the commit endpoint below
    once HR has reviewed the preview."""
    rows = _parse_bulk_csv_or_400(file)
    results = child_bulk_service.preview_bulk_add_children(
        db, rows=rows, added_by=current_hr_employee.employee_id
    )
    return BulkAddChildrenResponse.from_results(results)


@router.post("/hr/children/bulk/commit", response_model=BulkAddChildrenResponse)
def commit_bulk_add_children(
    file: UploadFile = File(...),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> BulkAddChildrenResponse:
    rows = _parse_bulk_csv_or_400(file)
    results = child_bulk_service.commit_bulk_add_children(
        db,
        rows=rows,
        added_by=current_hr_employee.employee_id,
        uploaded_file_name=file.filename,
    )
    return BulkAddChildrenResponse.from_results(results)


@router.get("/hr/children/bulk/history", response_model=list[BulkUploadBatchSummary])
def list_bulk_add_children_history(
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[BulkUploadBatchSummary]:
    batches = bulk_add_children_repository.get_batches(db)
    return [BulkUploadBatchSummary.from_orm_model(batch) for batch in batches]


@router.get("/hr/children/bulk/history/{bulk_upload_id}", response_model=BulkUploadBatchDetail)
def get_bulk_add_children_batch(
    bulk_upload_id: int,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> BulkUploadBatchDetail:
    batch = bulk_add_children_repository.get_batch_by_id(db, bulk_upload_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bulk upload not found."
        )
    rows = bulk_add_children_repository.get_rows_for_batch(db, bulk_upload_id)
    return BulkUploadBatchDetail(
        **BulkUploadBatchSummary.from_orm_model(batch).model_dump(),
        results=[BulkChildRowResult.from_orm_model(row) for row in rows],
    )


def _parse_bulk_csv_or_400(file: UploadFile) -> list[child_bulk_service._ParsedBulkRow]:
    try:
        return child_bulk_service.parse_bulk_child_csv(file.file.read())
    except (BulkFileFormatError, BulkRowLimitExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/hr/claims", response_model=list[HRClaimSummary])
def list_claims(
    status_filter: str | None = Query(default=None, alias="status"),
    employee_id: str | None = None,
    child_id: str | None = None,
    submitted_date_from: date | None = None,
    submitted_date_to: date | None = None,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[HRClaimSummary]:
    return hr_service.list_claims(
        db,
        status_filter,
        employee_id=employee_id,
        child_id=child_id,
        submitted_date_from=submitted_date_from,
        submitted_date_to=submitted_date_to,
    )


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
