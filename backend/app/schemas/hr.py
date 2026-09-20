from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.approval_history import ApprovalHistoryEntry
from app.schemas.attachment import AttachmentResponse
from app.schemas.eligibility import EligibilityResponse
from app.schemas.payout import PayoutScheduleEntry

if TYPE_CHECKING:
    from app.models.claim import ClaimMaster


class ApproveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approved_amount: Decimal = Field(gt=0)
    remarks: str | None = Field(default=None, max_length=1000)


class RejectRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    remarks: str = Field(min_length=1, max_length=1000)


class SendBackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    remarks: str = Field(min_length=1, max_length=1000)


class HRClaimSummary(BaseModel):
    claim_id: int
    employee_id: str
    employee_name: str
    child_id: str
    child_name: str
    invoice_date: date
    invoice_number: str
    invoice_amount: Decimal
    claim_amount: Decimal
    claim_status: str
    comments: str | None
    submitted_date: datetime | None
    requires_documents: bool

    @classmethod
    def from_orm_model(
        cls, claim: ClaimMaster, *, employee_name: str, child_name: str, requires_documents: bool
    ) -> HRClaimSummary:
        return cls(
            claim_id=claim.ClaimID,
            employee_id=claim.EmployeeID,
            employee_name=employee_name,
            child_id=claim.ChildID,
            child_name=child_name,
            invoice_date=claim.InvoiceDate,
            invoice_number=claim.InvoiceNumber,
            invoice_amount=claim.InvoiceAmount,
            claim_amount=claim.ClaimAmount,
            claim_status=claim.ClaimStatus,
            comments=claim.Comments,
            submitted_date=claim.SubmittedDate,
            requires_documents=requires_documents,
        )


class HRClaimDetail(HRClaimSummary):
    eligibility: EligibilityResponse | None
    attachments: list[AttachmentResponse]
    approval_history: list[ApprovalHistoryEntry]
    payout_schedule: list[PayoutScheduleEntry]
