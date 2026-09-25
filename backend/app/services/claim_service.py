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

Per user direction 2026-09-24, a claim also carries InstitutionName and a
From Date/To Date service period, validated against the child's age in
months (From Date >= 14 months, To Date <= 72 months) — these are
descriptive fields only and do not affect which EligibilityID the claim
posts against (still InvoiceDate) or payout allocation (still HR approval
time).

Per user direction 2026-09-25, HR can also globally block all new claim
creation/submission (Childcare_PayoutSettings.ClaimsBlocked) — checked in
both create_claim and submit_claim, but deliberately not in update_claim
(editing an already-created Draft) or anywhere in hr_service (HR's own
review actions continue normally while blocked).

submit_claim also snapshots the current SubmissionCutoffDay onto the
claim itself (ClaimMaster.SubmissionCutoffDayAtSubmission) rather than
letting payout_calculator.py re-read "whatever the setting is now" —
see that column's own comment for the bug this fixes.

Per user direction 2026-09-25 (same day), a claim also cannot be raised
for a financial year later than whichever one HR has most recently
opened (Childcare_PayoutSettings.OpenFinancialYearID) — checked in
_resolve_eligibility_for_invoice, so it applies to both create_claim and
update_claim (editing a Draft's invoice date is equivalent to choosing a
financial year all over again). This is a real, explicit gate, not one
that falls back to "the current calendar FY" on its own — see
payout_settings_service.is_financial_year_open's own comment for why.
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
    ClaimsBlockedError,
    DuplicateInvoiceError,
    FileTooLargeError,
    FinancialYearNotOpenError,
    FirstYearPayoutPeriodError,
    InvalidServicePeriodError,
    InvalidUploadError,
    NoEligibilityForPeriodError,
)
from app.models.child import ChildMaster
from app.models.claim import DRAFT, SENT_BACK
from app.models.eligibility import EligibilityMaster
from app.repositories import (
    child_repository,
    claim_approval_history_repository,
    claim_attachment_repository,
    claim_repository,
    eligibility_repository,
    employee_repository,
    payout_repository,
)
from app.schemas.approval_history import ApprovalHistoryEntry
from app.schemas.attachment import AttachmentResponse
from app.schemas.claim import ClaimCreateRequest, ClaimResponse, ClaimUpdateRequest
from app.schemas.employee import EmployeeProfile
from app.schemas.payout import PayoutScheduleEntry
from app.services import (
    eligibility_balance_service,
    eligibility_calculator,
    payout_settings_service,
)
from app.services.storage import minio_client


def _safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", base) or "file"


def _employee_display_name(db: Session, employee_id: str) -> str:
    employee = employee_repository.get_by_employee_id(db, employee_id)
    if employee is not None and employee.FullName:
        return employee.FullName
    return employee_id


def _get_child_or_raise(db: Session, employee: EmployeeProfile, child_id: str) -> ChildMaster:
    child = child_repository.get_child_for_employee(db, employee.memp_id, child_id)
    if child is None:
        raise ChildNotFoundError(f"No child {child_id} found for this employee.")
    return child


def _resolve_eligibility_for_invoice(
    db: Session, employee: EmployeeProfile, child: ChildMaster, invoice_date: date
) -> EligibilityMaster:
    if eligibility_calculator.is_first_year_payout_month(
        child_dob=child.ChildDOB, month=invoice_date
    ):
        raise FirstYearPayoutPeriodError(
            "No claim is needed for this period — the child's first 13 months are paid "
            "automatically."
        )

    fy = eligibility_calculator.compute_financial_year(invoice_date)
    if not payout_settings_service.is_financial_year_open(db, fy):
        raise FinancialYearNotOpenError(
            f"Claims for financial year {fy.label} are not open yet. Please contact HR."
        )
    rows = eligibility_repository.get_for_child(db, employee.memp_id, child.ChildID, fy.label)
    if not rows:
        raise NoEligibilityForPeriodError(
            f"No eligibility record exists for this child in financial year {fy.label}."
        )
    return rows[0]


def _validate_service_period(child: ChildMaster, from_date: date, to_date: date) -> None:
    """From Date/To Date are descriptive fields recording the service
    period an institution's invoice covers (user direction 2026-09-24) —
    they don't affect which EligibilityID the claim posts against (still
    InvoiceDate) or payout allocation (still HR approval time), but are
    validated against the child's age in months so a claim can't be
    raised for a period that was never claimable in the first place."""
    if not eligibility_calculator.is_valid_claim_from_date(
        child_dob=child.ChildDOB, from_date=from_date
    ):
        raise InvalidServicePeriodError(
            "From Date must be at least 14 months after the child's date of birth — the "
            "first 13 months are paid automatically, with no claim needed."
        )
    if not eligibility_calculator.is_valid_claim_to_date(child_dob=child.ChildDOB, to_date=to_date):
        raise InvalidServicePeriodError(
            "To Date cannot be more than 72 months (6 years) after the child's date of birth."
        )


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
        ApprovalHistoryEntry.from_orm_model(
            h, action_by_name=_employee_display_name(db, h.ActionBy)
        )
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


def _require_claims_not_blocked(db: Session) -> None:
    if payout_settings_service.get_settings(db).claims_blocked:
        raise ClaimsBlockedError(
            "HR has temporarily paused new claim submissions. Please try again later."
        )


def create_claim(
    db: Session, employee: EmployeeProfile, payload: ClaimCreateRequest
) -> ClaimResponse:
    _require_claims_not_blocked(db)
    _check_duplicate_invoice(db, employee, payload.child_id, payload.invoice_number)
    child = _get_child_or_raise(db, employee, payload.child_id)
    eligibility = _resolve_eligibility_for_invoice(db, employee, child, payload.invoice_date)
    _validate_service_period(child, payload.from_date, payload.to_date)
    claim = claim_repository.create_claim(
        db,
        memp_id=employee.memp_id,
        employee_id=employee.employee_id,
        child_id=payload.child_id,
        eligibility_id=eligibility.EligibilityID,
        invoice_date=payload.invoice_date,
        invoice_number=payload.invoice_number,
        invoice_amount=payload.invoice_amount,
        institution_name=payload.institution_name,
        from_date=payload.from_date,
        to_date=payload.to_date,
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
    child = _get_child_or_raise(db, employee, claim.ChildID)
    eligibility = _resolve_eligibility_for_invoice(db, employee, child, payload.invoice_date)
    _validate_service_period(child, payload.from_date, payload.to_date)
    claim_repository.update_claim(
        db,
        claim,
        eligibility_id=eligibility.EligibilityID,
        invoice_date=payload.invoice_date,
        invoice_number=payload.invoice_number,
        invoice_amount=payload.invoice_amount,
        institution_name=payload.institution_name,
        from_date=payload.from_date,
        to_date=payload.to_date,
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
    _require_claims_not_blocked(db)
    # Document-requirement enforcement is intentionally disabled for now —
    # see the module docstring and DECISIONS_LOG.md item 38. The
    # `requires_documents` flag in the response still tells the client
    # whether documents would normally be expected.
    current_cutoff_day = payout_settings_service.get_settings(db).submission_cutoff_day
    claim_repository.mark_submitted(db, claim, submission_cutoff_day=current_cutoff_day)
    eligibility_balance_service.sync_balance(db, claim.EligibilityID)
    return _to_response(db, claim)


def delete_claim(db: Session, employee: EmployeeProfile, claim_id: int) -> None:
    """Only a Draft claim can be deleted (user direction 2026-09-25) — a
    SentBack claim should be corrected and resubmitted instead, matching
    how it's already treated everywhere else (_EDITABLE_STATUSES covers
    both for editing, but deletion is Draft-only). No balance resync is
    needed: Draft claims never count toward InProgressAmount (only
    Submitted does — see report_repository.
    get_in_progress_totals_by_eligibility), so nothing they've never
    touched needs recomputing."""
    claim = claim_repository.get_claim_for_employee(db, employee.memp_id, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found for this employee.")
    if claim.ClaimStatus != DRAFT:
        raise ClaimNotEditableError("Only a Draft claim can be deleted.")
    claim_attachment_repository.delete_for_claim(db, claim.ClaimID)
    claim_repository.delete_claim(db, claim)


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
