"""Claim + document upload business logic.

Per DATA_VALIDATION_RULES.md: a claim's child must belong to the
authenticated employee, and an eligibility record must exist for the
financial year the claim's invoice date falls in.

Per user direction 2026-09-19 (see DECISIONS_LOG.md item 38), the
document-upload requirement for the child's 13th month of life (from DOB)
or later is *not* enforced as a submission blocker for now — the
`requires_documents` flag returned to the client is still computed and
shown, but a claim may be submitted with or without documents.

Per user direction 2026-09-19 (see DECISIONS_LOG.md item 39), a claim
cannot be created or edited to have the same invoice number as another
existing claim for the same employee and child, regardless of that other
claim's status.

Per user direction 2026-09-20 (see DECISIONS_LOG.md item 44),
Childcare_EligibilityMaster's UtilizedAmount/ApprovedAmount/
InProgressAmount/RemainingAmount are now maintained balances (superseding
item 20 for these specific columns) — submitting a claim here triggers a
recompute via eligibility_balance_service, since it changes which claims
count toward "In Progress".
"""
import io
import re
import uuid
from datetime import date
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    AttachmentNotFoundError,
    ChildNotFoundError,
    ClaimNotEditableError,
    ClaimNotFoundError,
    DuplicateInvoiceError,
    FileTooLargeError,
    InvalidUploadError,
    NoEligibilityForPeriodError,
)
from app.models.claim import DRAFT, SENT_BACK
from app.models.eligibility import EligibilityMaster
from app.repositories import (
    child_repository,
    claim_approval_history_repository,
    claim_attachment_repository,
    claim_repository,
    eligibility_repository,
    payout_repository,
)
from app.schemas.approval_history import ApprovalHistoryEntry
from app.schemas.attachment import AttachmentResponse
from app.schemas.claim import ClaimCreateRequest, ClaimResponse, ClaimUpdateRequest
from app.schemas.employee import EmployeeProfile
from app.schemas.payout import PayoutScheduleEntry
from app.services import eligibility_balance_service, eligibility_calculator
from app.services.storage import minio_client


def _safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", base) or "file"


def _resolve_eligibility_for_invoice(
    db: Session, employee: EmployeeProfile, child_id: str, invoice_date: date
) -> EligibilityMaster:
    child = child_repository.get_child_for_employee(db, employee.memp_id, child_id)
    if child is None:
        raise ChildNotFoundError(f"No child {child_id} found for this employee.")

    fy = eligibility_calculator.compute_financial_year(invoice_date)
    rows = eligibility_repository.get_for_child(db, employee.memp_id, child_id, fy.label)
    if not rows:
        raise NoEligibilityForPeriodError(
            f"No eligibility record exists for this child in financial year {fy.label}."
        )
    return rows[0]


def _check_duplicate_invoice(
    db: Session,
    employee: EmployeeProfile,
    child_id: str,
    invoice_number: str,
    *,
    exclude_claim_id: int | None = None,
) -> None:
    existing = claim_repository.get_by_invoice(
        db, employee.memp_id, child_id, invoice_number, exclude_claim_id=exclude_claim_id
    )
    if existing is not None:
        raise DuplicateInvoiceError(
            f"A claim with invoice number {invoice_number!r} already exists for this child."
        )


def _to_response(db: Session, claim) -> ClaimResponse:
    child = child_repository.get_child_by_id(db, claim.ChildID)
    # A claim's ChildID is a foreign key into Childcare_ChildMaster, so the
    # row is guaranteed to exist.
    assert child is not None
    requires_documents = eligibility_calculator.claim_requires_documents(
        child_dob=child.ChildDOB, invoice_date=claim.InvoiceDate
    )
    attachments = [
        AttachmentResponse.from_orm_model(a)
        for a in claim_attachment_repository.get_for_claim(db, claim.ClaimID)
    ]
    approval_history = [
        ApprovalHistoryEntry.from_orm_model(h)
        for h in claim_approval_history_repository.get_for_claim(db, claim.ClaimID)
    ]
    payout_schedule = [
        PayoutScheduleEntry.from_orm_model(a)
        for a in payout_repository.get_allocations_for_claim(db, claim.ClaimID)
    ]
    return ClaimResponse.from_orm_model(
        claim,
        child_name=child.ChildName,
        requires_documents=requires_documents,
        attachments=attachments,
        approval_history=approval_history,
        payout_schedule=payout_schedule,
    )


def create_claim(
    db: Session, employee: EmployeeProfile, payload: ClaimCreateRequest
) -> ClaimResponse:
    _check_duplicate_invoice(db, employee, payload.child_id, payload.invoice_number)
    eligibility = _resolve_eligibility_for_invoice(
        db, employee, payload.child_id, payload.invoice_date
    )
    claim = claim_repository.create_claim(
        db,
        memp_id=employee.memp_id,
        employee_id=employee.employee_id,
        child_id=payload.child_id,
        eligibility_id=eligibility.EligibilityID,
        invoice_date=payload.invoice_date,
        invoice_number=payload.invoice_number,
        invoice_amount=payload.invoice_amount,
        comments=payload.comments,
        created_by=employee.employee_id,
    )
    return _to_response(db, claim)


_EDITABLE_STATUSES = {DRAFT, SENT_BACK}


def _get_owned_editable_claim(db: Session, employee: EmployeeProfile, claim_id: int):
    """A Draft claim can be edited/submitted for the first time; a
    SentBack claim can be corrected and resubmitted per
    CODEX_MASTER_INSTRUCTIONS.md §9. No other status is editable."""
    claim = claim_repository.get_claim_for_employee(db, employee.memp_id, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found for this employee.")
    if claim.ClaimStatus not in _EDITABLE_STATUSES:
        raise ClaimNotEditableError(
            "Only a Draft or Sent Back claim can be edited or submitted."
        )
    return claim


def update_claim(
    db: Session, employee: EmployeeProfile, claim_id: int, payload: ClaimUpdateRequest
) -> ClaimResponse:
    claim = _get_owned_editable_claim(db, employee, claim_id)
    _check_duplicate_invoice(
        db,
        employee,
        claim.ChildID,
        payload.invoice_number,
        exclude_claim_id=claim.ClaimID,
    )
    eligibility = _resolve_eligibility_for_invoice(
        db, employee, claim.ChildID, payload.invoice_date
    )
    claim_repository.update_claim(
        db,
        claim,
        eligibility_id=eligibility.EligibilityID,
        invoice_date=payload.invoice_date,
        invoice_number=payload.invoice_number,
        invoice_amount=payload.invoice_amount,
        comments=payload.comments,
        updated_by=employee.employee_id,
    )
    return _to_response(db, claim)


def list_claims(db: Session, employee: EmployeeProfile) -> list[ClaimResponse]:
    claims = claim_repository.get_claims_for_employee(db, employee.memp_id)
    return [_to_response(db, claim) for claim in claims]


def get_claim(db: Session, employee: EmployeeProfile, claim_id: int) -> ClaimResponse:
    claim = claim_repository.get_claim_for_employee(db, employee.memp_id, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found for this employee.")
    return _to_response(db, claim)


def submit_claim(db: Session, employee: EmployeeProfile, claim_id: int) -> ClaimResponse:
    claim = _get_owned_editable_claim(db, employee, claim_id)
    # Document-requirement enforcement is intentionally disabled for now —
    # see the module docstring and DECISIONS_LOG.md item 38. The
    # `requires_documents` flag in the response still tells the client
    # whether documents would normally be expected.
    claim_repository.mark_submitted(db, claim)
    eligibility_balance_service.sync_balance(db, claim.EligibilityID)
    return _to_response(db, claim)


def upload_attachment(
    db: Session,
    employee: EmployeeProfile,
    claim_id: int,
    attachment_type: str,
    *,
    filename: str,
    content_type: str | None,
    file_stream: BinaryIO,
) -> AttachmentResponse:
    claim = _get_owned_editable_claim(db, employee, claim_id)
    settings = get_settings()

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in settings.allowed_upload_extensions_set:
        raise InvalidUploadError(
            f"File type .{extension or '(none)'} is not allowed. "
            f"Allowed types: {', '.join(sorted(settings.allowed_upload_extensions_set))}."
        )

    contents = file_stream.read()
    size = len(contents)
    if size == 0:
        raise InvalidUploadError("Uploaded file is empty.")
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size > max_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_size_mb} MB limit.")

    stored_name = f"{uuid.uuid4()}-{_safe_filename(filename)}"
    object_key = f"claims/{employee.employee_id}/{claim.ChildID}/{claim.ClaimID}/{stored_name}"
    resolved_content_type = content_type or "application/octet-stream"

    # Uploaded to MinIO before the metadata row is written: if the DB
    # insert below ever failed, the result is a harmless orphaned object
    # in MinIO, never a DB row pointing at a file that doesn't exist.
    client = minio_client.get_minio_client()
    minio_client.upload_object(
        client,
        bucket_name=settings.minio_bucket_name,
        object_key=object_key,
        data=io.BytesIO(contents),
        length=size,
        content_type=resolved_content_type,
    )

    attachment = claim_attachment_repository.create_attachment(
        db,
        claim_id=claim.ClaimID,
        attachment_type=attachment_type,
        original_file_name=filename,
        stored_file_name=stored_name,
        bucket_name=settings.minio_bucket_name,
        object_key=object_key,
        content_type=resolved_content_type,
        file_size=size,
        uploaded_by=employee.employee_id,
    )
    return AttachmentResponse.from_orm_model(attachment)


def list_attachments(
    db: Session, employee: EmployeeProfile, claim_id: int
) -> list[AttachmentResponse]:
    claim = claim_repository.get_claim_for_employee(db, employee.memp_id, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found for this employee.")
    return [
        AttachmentResponse.from_orm_model(a)
        for a in claim_attachment_repository.get_for_claim(db, claim.ClaimID)
    ]


def get_attachment_download_url(
    db: Session, employee: EmployeeProfile, claim_id: int, attachment_id: int
) -> str:
    claim = claim_repository.get_claim_for_employee(db, employee.memp_id, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found for this employee.")

    attachment = claim_attachment_repository.get_attachment_for_claim(
        db, claim.ClaimID, attachment_id
    )
    if attachment is None:
        raise AttachmentNotFoundError(f"No attachment {attachment_id} found for this claim.")

    client = minio_client.get_minio_client()
    return minio_client.get_presigned_download_url(
        client, bucket_name=attachment.BucketName, object_key=attachment.ObjectKey
    )
