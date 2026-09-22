"""HR claim review business logic.

Per CODEX_MASTER_INSTRUCTIONS.md §11, every HR action (Approve/Reject/Send
Back) is recorded in Childcare_ClaimApprovalHistory, atomically with the
status change. Authorization (is this employee a recognized, active HR
approver) is enforced by app/dependencies/auth.py's
get_current_hr_approver — every route here requires that dependency, so
this module does not re-check it.

Per user direction 2026-09-20 (see DECISIONS_LOG.md item 44),
Childcare_EligibilityMaster's Utilized/Approved/InProgress/RemainingAmount
are now maintained balances (superseding item 20 for these specific
columns): approving, rejecting, or sending back a claim here triggers a
recompute via eligibility_balance_service, and an approval is rejected if
the requested amount would exceed the child's remaining balance for that
financial year.

Approving a claim also triggers payout_service.recalculate_payout, which
fully rebuilds that child's financial-year monthly payout ledger and
per-claim allocation — see PAYOUT_REQUIREMENTS.md and DECISIONS_LOG.md
items 44-49. Rejecting or sending back a claim does not, since it was
never Approved in the first place and therefore never had a payout
allocation to begin with.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import (
    AttachmentNotFoundError,
    ClaimNotFoundError,
    ClaimNotReviewableError,
    InvalidApprovedAmountError,
)
from app.models.claim import APPROVED, REJECTED, SENT_BACK, SUBMITTED, ClaimMaster
from app.repositories import (
    child_repository,
    claim_approval_history_repository,
    claim_attachment_repository,
    claim_repository,
    eligibility_repository,
    employee_repository,
    payout_repository,
)
from app.schemas.attachment import AttachmentResponse
from app.schemas.eligibility import EligibilityResponse
from app.schemas.hr import (
    ApprovalHistoryEntry,
    ApproveRequest,
    HRClaimDetail,
    HRClaimSummary,
    RejectRequest,
    SendBackRequest,
)
from app.schemas.payout import PayoutScheduleEntry
from app.services import eligibility_balance_service, eligibility_calculator, payout_service
from app.services.storage import minio_client


def _employee_display_name(db: Session, employee_id: str) -> str:
    employee = employee_repository.get_by_employee_id(db, employee_id)
    if employee is not None and employee.FullName:
        return employee.FullName
    return employee_id


def _to_summary(
    claim: ClaimMaster, *, employee_name: str, child_name: str, child_dob: date
) -> HRClaimSummary:
    requires_documents = eligibility_calculator.claim_requires_documents(
        child_dob=child_dob, invoice_date=claim.InvoiceDate
    )
    return HRClaimSummary.from_orm_model(
        claim,
        employee_name=employee_name,
        child_name=child_name,
        requires_documents=requires_documents,
    )


def list_claims(
    db: Session,
    status: str | None = None,
    *,
    employee_id: str | None = None,
    child_id: str | None = None,
) -> list[HRClaimSummary]:
    """Batches the employee-name and child lookups (one query each for the
    whole list) rather than querying per claim — this endpoint's result
    set grows with total claims across all employees, not just one
    employee's own, so an N+1 pattern here scales badly.

    `employee_id`/`child_id` are used by the claim detail page's "claim
    history" popup, to show every other claim for the same employee+child
    without mixing in the employee's other children's claims."""
    claims = claim_repository.get_claims_for_hr(
        db, status, employee_id=employee_id, child_id=child_id
    )

    child_by_id = {child.ChildID: child for child in child_repository.get_all_active_children(db)}
    employee_names = employee_repository.get_names_by_employee_ids(
        db, [claim.EmployeeID for claim in claims]
    )

    summaries = []
    for claim in claims:
        child = child_by_id.get(claim.ChildID)
        if child is None:
            # Defensive fallback only — ChildID is a foreign key, so this
            # should be unreachable in practice.
            child = child_repository.get_child_by_id(db, claim.ChildID)
        assert child is not None
        summaries.append(
            _to_summary(
                claim,
                employee_name=employee_names.get(claim.EmployeeID, claim.EmployeeID),
                child_name=child.ChildName,
                child_dob=child.ChildDOB,
            )
        )
    return summaries


def get_claim_detail(db: Session, claim_id: int) -> HRClaimDetail:
    claim = claim_repository.get_claim_by_id(db, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found.")

    child = child_repository.get_child_by_id(db, claim.ChildID)
    assert child is not None
    summary = _to_summary(
        claim,
        employee_name=_employee_display_name(db, claim.EmployeeID),
        child_name=child.ChildName,
        child_dob=child.ChildDOB,
    )
    eligibility = eligibility_repository.get_by_id(db, claim.EligibilityID)
    attachments = [
        AttachmentResponse.from_orm_model(a)
        for a in claim_attachment_repository.get_for_claim(db, claim.ClaimID)
    ]
    history = [
        ApprovalHistoryEntry.from_orm_model(
            h, action_by_name=_employee_display_name(db, h.ActionBy)
        )
        for h in claim_approval_history_repository.get_for_claim(db, claim.ClaimID)
    ]
    payout_schedule = [
        PayoutScheduleEntry.from_orm_model(a)
        for a in payout_repository.get_allocations_for_claim(db, claim.ClaimID)
    ]

    return HRClaimDetail(
        **summary.model_dump(),
        eligibility=EligibilityResponse.from_orm_model(eligibility) if eligibility else None,
        attachments=attachments,
        approval_history=history,
        payout_schedule=payout_schedule,
    )


def _require_reviewable_claim(db: Session, claim_id: int) -> ClaimMaster:
    # Row-locked: without this, two concurrent requests for the same claim
    # (a slow request plus an impatient double-click, or a client retry)
    # can both read ClaimStatus == Submitted before either commits, and
    # both proceed — see DECISIONS_LOG.md item 55.
    claim = claim_repository.get_claim_by_id_for_update(db, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found.")
    if claim.ClaimStatus != SUBMITTED:
        raise ClaimNotReviewableError(
            "Only a Submitted claim can be approved, rejected, or sent back."
        )
    return claim


def approve_claim(
    db: Session, hr_employee_id: str, claim_id: int, payload: ApproveRequest
) -> HRClaimDetail:
    claim = _require_reviewable_claim(db, claim_id)
    if payload.approved_amount > claim.InvoiceAmount:
        raise InvalidApprovedAmountError("Approved amount cannot exceed the invoice amount.")

    # Row-locked so two concurrent approvals against the same child+FY
    # can't both read the same stale balance and together over-spend it —
    # see DECISIONS_LOG.md item 44.
    eligibility = eligibility_repository.get_by_id_for_update(db, claim.EligibilityID)
    assert eligibility is not None
    if payload.approved_amount > eligibility.RemainingAmount:
        raise InvalidApprovedAmountError(
            f"Approved amount exceeds the remaining balance "
            f"({eligibility.RemainingAmount}) for this child's "
            f"{eligibility.FinancialYear} eligibility."
        )

    previous_status = claim.ClaimStatus
    claim_repository.set_status(db, claim, APPROVED)
    claim_approval_history_repository.create_entry(
        db,
        claim_id=claim.ClaimID,
        action_by=hr_employee_id,
        action=APPROVED,
        previous_status=previous_status,
        new_status=APPROVED,
        approved_amount=payload.approved_amount,
        remarks=payload.remarks,
    )
    eligibility_balance_service.sync_balance(db, claim.EligibilityID)
    payout_service.recalculate_payout(db, claim.EligibilityID)
    return get_claim_detail(db, claim_id)


def reject_claim(
    db: Session, hr_employee_id: str, claim_id: int, payload: RejectRequest
) -> HRClaimDetail:
    claim = _require_reviewable_claim(db, claim_id)

    previous_status = claim.ClaimStatus
    claim_repository.set_status(db, claim, REJECTED)
    claim_approval_history_repository.create_entry(
        db,
        claim_id=claim.ClaimID,
        action_by=hr_employee_id,
        action=REJECTED,
        previous_status=previous_status,
        new_status=REJECTED,
        approved_amount=None,
        remarks=payload.remarks,
    )
    eligibility_balance_service.sync_balance(db, claim.EligibilityID)
    return get_claim_detail(db, claim_id)


def send_back_claim(
    db: Session, hr_employee_id: str, claim_id: int, payload: SendBackRequest
) -> HRClaimDetail:
    claim = _require_reviewable_claim(db, claim_id)

    previous_status = claim.ClaimStatus
    claim_repository.set_status(db, claim, SENT_BACK)
    claim_approval_history_repository.create_entry(
        db,
        claim_id=claim.ClaimID,
        action_by=hr_employee_id,
        action=SENT_BACK,
        previous_status=previous_status,
        new_status=SENT_BACK,
        approved_amount=None,
        remarks=payload.remarks,
    )
    eligibility_balance_service.sync_balance(db, claim.EligibilityID)
    return get_claim_detail(db, claim_id)


def list_attachments(db: Session, claim_id: int) -> list[AttachmentResponse]:
    claim = claim_repository.get_claim_by_id(db, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found.")
    return [
        AttachmentResponse.from_orm_model(a)
        for a in claim_attachment_repository.get_for_claim(db, claim.ClaimID)
    ]


def get_attachment_download_url(db: Session, claim_id: int, attachment_id: int) -> str:
    claim = claim_repository.get_claim_by_id(db, claim_id)
    if claim is None:
        raise ClaimNotFoundError(f"No claim {claim_id} found.")

    attachment = claim_attachment_repository.get_attachment_for_claim(
        db, claim.ClaimID, attachment_id
    )
    if attachment is None:
        raise AttachmentNotFoundError(f"No attachment {attachment_id} found for this claim.")

    client = minio_client.get_minio_client()
    return minio_client.get_presigned_download_url(
        client, bucket_name=attachment.BucketName, object_key=attachment.ObjectKey
    )
