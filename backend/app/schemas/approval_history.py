from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.claim_approval_history import ClaimApprovalHistory


class ApprovalHistoryEntry(BaseModel):
    approval_history_id: int
    action_by: str
    action: str
    previous_status: str
    new_status: str
    approved_amount: Decimal | None
    remarks: str | None
    action_date: datetime

    @classmethod
    def from_orm_model(cls, entry: ClaimApprovalHistory) -> ApprovalHistoryEntry:
        return cls(
            approval_history_id=entry.ApprovalHistoryID,
            action_by=entry.ActionBy,
            action=entry.Action,
            previous_status=entry.PreviousStatus,
            new_status=entry.NewStatus,
            approved_amount=entry.ApprovedAmount,
            remarks=entry.Remarks,
            action_date=entry.ActionDate,
        )
