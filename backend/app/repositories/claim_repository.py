from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import DRAFT, SUBMITTED, ClaimMaster


def _utc_now_naive() -> datetime:
    """A naive UTC datetime, matching CreatedDate columns' GETUTCDATE()
    server default convention, for the DATETIME columns this repository
    sets from application code."""
    return datetime.now(UTC).replace(tzinfo=None)


def get_claims_for_employee(db: Session, memp_id: int) -> list[ClaimMaster]:
    return list(
        db.execute(
            select(ClaimMaster)
            .where(ClaimMaster.MEmpID == memp_id)
            .order_by(ClaimMaster.CreatedDate.desc())
        )
        .scalars()
        .all()
    )


def get_claim_for_employee(db: Session, memp_id: int, claim_id: int) -> ClaimMaster | None:
    return db.execute(
        select(ClaimMaster).where(ClaimMaster.MEmpID == memp_id, ClaimMaster.ClaimID == claim_id)
    ).scalar_one_or_none()


def get_by_invoice(
    db: Session,
    memp_id: int,
    child_id: str,
    invoice_number: str,
    *,
    exclude_claim_id: int | None = None,
) -> ClaimMaster | None:
    """Looks up any existing claim (regardless of status) for this
    employee/child/invoice-number combination, for the duplicate-invoice
    check — see DECISIONS_LOG.md item 39."""
    stmt = select(ClaimMaster).where(
        ClaimMaster.MEmpID == memp_id,
        ClaimMaster.ChildID == child_id,
        ClaimMaster.InvoiceNumber == invoice_number,
    )
    if exclude_claim_id is not None:
        stmt = stmt.where(ClaimMaster.ClaimID != exclude_claim_id)
    return db.execute(stmt).scalars().first()


def create_claim(
    db: Session,
    *,
    memp_id: int,
    employee_id: str,
    child_id: str,
    eligibility_id: int,
    invoice_date: date,
    invoice_number: str,
    invoice_amount: Decimal,
    comments: str | None,
    created_by: str,
) -> ClaimMaster:
    claim = ClaimMaster(
        MEmpID=memp_id,
        EmployeeID=employee_id,
        ChildID=child_id,
        EligibilityID=eligibility_id,
        InvoiceDate=invoice_date,
        InvoiceNumber=invoice_number,
        InvoiceAmount=invoice_amount,
        # See DECISIONS_LOG.md item 18: mirrors InvoiceAmount at creation —
        # the employee is not asked for a separate claim amount.
        ClaimAmount=invoice_amount,
        ClaimStatus=DRAFT,
        Comments=comments,
        CreatedBy=created_by,
    )
    db.add(claim)
    db.flush()
    return claim


def update_claim(
    db: Session,
    claim: ClaimMaster,
    *,
    eligibility_id: int,
    invoice_date: date,
    invoice_number: str,
    invoice_amount: Decimal,
    comments: str | None,
    updated_by: str,
) -> ClaimMaster:
    claim.EligibilityID = eligibility_id
    claim.InvoiceDate = invoice_date
    claim.InvoiceNumber = invoice_number
    claim.InvoiceAmount = invoice_amount
    claim.ClaimAmount = invoice_amount
    claim.Comments = comments
    claim.UpdatedBy = updated_by
    claim.UpdatedDate = _utc_now_naive()
    db.flush()
    return claim


def mark_submitted(db: Session, claim: ClaimMaster) -> ClaimMaster:
    claim.ClaimStatus = SUBMITTED
    claim.SubmittedDate = _utc_now_naive()
    db.flush()
    return claim


def get_claim_by_id(db: Session, claim_id: int) -> ClaimMaster | None:
    """Unscoped lookup for HR use — HR is not restricted to a subset of
    employees' claims, only to being a recognized active HR approver
    (enforced by the get_current_hr_approver dependency)."""
    return db.execute(
        select(ClaimMaster).where(ClaimMaster.ClaimID == claim_id)
    ).scalar_one_or_none()


def get_claims_for_hr(
    db: Session,
    status: str | None = None,
    *,
    employee_id: str | None = None,
    child_id: str | None = None,
) -> list[ClaimMaster]:
    stmt = select(ClaimMaster)
    if status is not None:
        stmt = stmt.where(ClaimMaster.ClaimStatus == status)
    if employee_id is not None:
        stmt = stmt.where(ClaimMaster.EmployeeID == employee_id)
    if child_id is not None:
        stmt = stmt.where(ClaimMaster.ChildID == child_id)
    return list(db.execute(stmt.order_by(ClaimMaster.CreatedDate.desc())).scalars().all())


def set_status(db: Session, claim: ClaimMaster, new_status: str) -> ClaimMaster:
    claim.ClaimStatus = new_status
    db.flush()
    return claim
