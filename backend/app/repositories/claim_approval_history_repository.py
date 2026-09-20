from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim_approval_history import ClaimApprovalHistory


def create_entry(
    db: Session,
    *,
    claim_id: int,
    action_by: str,
    action: str,
    previous_status: str,
    new_status: str,
    approved_amount: Decimal | None,
    remarks: str | None,
) -> ClaimApprovalHistory:
    entry = ClaimApprovalHistory(
        ClaimID=claim_id,
        ActionBy=action_by,
        Action=action,
        PreviousStatus=previous_status,
        NewStatus=new_status,
        ApprovedAmount=approved_amount,
        Remarks=remarks,
    )
    db.add(entry)
    db.flush()
    return entry


def get_for_claim(db: Session, claim_id: int) -> list[ClaimApprovalHistory]:
    return list(
        db.execute(
            select(ClaimApprovalHistory)
            .where(ClaimApprovalHistory.ClaimID == claim_id)
            .order_by(ClaimApprovalHistory.ActionDate)
        )
        .scalars()
        .all()
    )
