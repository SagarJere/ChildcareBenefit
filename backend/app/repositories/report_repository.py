"""Data access for HR reports and the employee-facing eligibility report.

Aggregate figures here (approved/in-progress totals) are computed live
from Childcare_ClaimApprovalHistory and Childcare_ClaimMaster — never
from Childcare_EligibilityMaster's own Utilized/Approved/InProgress/
RemainingAmount columns, which this application never updates (see
DECISIONS_LOG.md items 20, 26, 32).
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.claim import SUBMITTED, ClaimMaster
from app.models.claim_approval_history import APPROVED as HISTORY_APPROVED
from app.models.claim_approval_history import ClaimApprovalHistory
from app.models.eligibility import EligibilityMaster


def get_claims_for_report(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    employee_id: str | None = None,
) -> list[ClaimMaster]:
    stmt = select(ClaimMaster)
    if date_from is not None:
        stmt = stmt.where(ClaimMaster.InvoiceDate >= date_from)
    if date_to is not None:
        stmt = stmt.where(ClaimMaster.InvoiceDate <= date_to)
    if status is not None:
        stmt = stmt.where(ClaimMaster.ClaimStatus == status)
    if employee_id is not None:
        stmt = stmt.where(ClaimMaster.EmployeeID == employee_id)
    stmt = stmt.order_by(ClaimMaster.InvoiceDate.desc())
    return list(db.execute(stmt).scalars().all())


def get_approved_totals_by_eligibility(
    db: Session, eligibility_ids: list[int]
) -> dict[int, Decimal]:
    """SUM of ApprovedAmount per EligibilityID, for claims whose approval
    history has an 'Approved' entry (a claim is approved at most once in
    this application, so there is exactly one such entry per approved
    claim)."""
    if not eligibility_ids:
        return {}

    rows = db.execute(
        select(ClaimMaster.EligibilityID, func.sum(ClaimApprovalHistory.ApprovedAmount))
        .join(ClaimApprovalHistory, ClaimApprovalHistory.ClaimID == ClaimMaster.ClaimID)
        .where(
            ClaimMaster.EligibilityID.in_(eligibility_ids),
            ClaimApprovalHistory.Action == HISTORY_APPROVED,
        )
        .group_by(ClaimMaster.EligibilityID)
    ).all()
    return {eligibility_id: total for eligibility_id, total in rows if total is not None}


def get_approved_dates_by_claim(db: Session, claim_ids: list[int]) -> dict[int, datetime]:
    """The ActionDate of each claim's 'Approved' history entry (a claim is
    approved at most once in this application — see
    get_approved_totals_by_eligibility), for the Claims Summary report's
    "Approved date" column."""
    if not claim_ids:
        return {}

    rows = db.execute(
        select(ClaimApprovalHistory.ClaimID, ClaimApprovalHistory.ActionDate).where(
            ClaimApprovalHistory.ClaimID.in_(claim_ids),
            ClaimApprovalHistory.Action == HISTORY_APPROVED,
        )
    ).all()
    return {claim_id: action_date for claim_id, action_date in rows}


def get_in_progress_totals_by_eligibility(
    db: Session, eligibility_ids: list[int]
) -> dict[int, Decimal]:
    """SUM of ClaimAmount per EligibilityID, for claims currently awaiting
    an HR decision (status Submitted)."""
    if not eligibility_ids:
        return {}

    rows = db.execute(
        select(ClaimMaster.EligibilityID, func.sum(ClaimMaster.ClaimAmount))
        .where(
            ClaimMaster.EligibilityID.in_(eligibility_ids),
            ClaimMaster.ClaimStatus == SUBMITTED,
        )
        .group_by(ClaimMaster.EligibilityID)
    ).all()
    return {eligibility_id: total for eligibility_id, total in rows if total is not None}


def get_last_activity_by_eligibility(
    db: Session, eligibility_ids: list[int]
) -> dict[int, datetime]:
    """The latest claim-related activity per EligibilityID — a claim being
    created/edited/submitted, or an HR action recorded against it. Used as
    "last modified" for eligibility reports, since EligibilityMaster's own
    CreatedDate never changes after the row is first created."""
    if not eligibility_ids:
        return {}

    claims = db.execute(
        select(
            ClaimMaster.ClaimID,
            ClaimMaster.EligibilityID,
            ClaimMaster.CreatedDate,
            ClaimMaster.UpdatedDate,
            ClaimMaster.SubmittedDate,
        ).where(ClaimMaster.EligibilityID.in_(eligibility_ids))
    ).all()

    latest: dict[int, datetime] = {}
    claim_to_eligibility: dict[int, int] = {}
    for claim_id, eligibility_id, created_date, updated_date, submitted_date in claims:
        claim_to_eligibility[claim_id] = eligibility_id
        for candidate in (created_date, updated_date, submitted_date):
            if candidate is not None and (
                eligibility_id not in latest or candidate > latest[eligibility_id]
            ):
                latest[eligibility_id] = candidate

    if claim_to_eligibility:
        history_rows = db.execute(
            select(ClaimApprovalHistory.ClaimID, ClaimApprovalHistory.ActionDate).where(
                ClaimApprovalHistory.ClaimID.in_(claim_to_eligibility.keys())
            )
        ).all()
        for claim_id, action_date in history_rows:
            eligibility_id = claim_to_eligibility[claim_id]
            if eligibility_id not in latest or action_date > latest[eligibility_id]:
                latest[eligibility_id] = action_date

    return latest


def get_all_eligibility(
    db: Session, *, financial_year: str | None = None, employee_id: str | None = None
) -> list[EligibilityMaster]:
    """Unscoped (across all employees) — for HR reports only."""
    stmt = select(EligibilityMaster)
    if financial_year is not None:
        stmt = stmt.where(EligibilityMaster.FinancialYear == financial_year)
    if employee_id is not None:
        stmt = stmt.where(EligibilityMaster.EmployeeID == employee_id)
    return list(db.execute(stmt.order_by(EligibilityMaster.CreatedDate)).scalars().all())
