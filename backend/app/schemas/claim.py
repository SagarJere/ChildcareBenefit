from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.approval_history import ApprovalHistoryEntry
from app.schemas.attachment import AttachmentResponse
from app.schemas.payout import PayoutScheduleEntry

if TYPE_CHECKING:
    from app.models.claim import ClaimMaster


class ClaimCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    child_id: str = Field(min_length=1, max_length=30)
    invoice_date: date
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_amount: Decimal = Field(gt=0)
    comments: str | None = Field(default=None, max_length=1000)

    @field_validator("invoice_date")
    @classmethod
    def invoice_date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Invoice date cannot be in the future.")
        return value


class ClaimUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_date: date
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_amount: Decimal = Field(gt=0)
    comments: str | None = Field(default=None, max_length=1000)

    @field_validator("invoice_date")
    @classmethod
    def invoice_date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Invoice date cannot be in the future.")
        return value


class ClaimResponse(BaseModel):
    claim_id: int
    child_id: str
    child_name: str
    eligibility_id: int
    invoice_date: date
    invoice_number: str
    invoice_amount: Decimal
    claim_amount: Decimal
    claim_status: str
    comments: str | None
    submitted_date: datetime | None
    created_date: datetime
    requires_documents: bool
    attachments: list[AttachmentResponse]
    approval_history: list[ApprovalHistoryEntry]
    payout_schedule: list[PayoutScheduleEntry]

    @classmethod
    def from_orm_model(
        cls,
        claim: ClaimMaster,
        *,
        child_name: str,
        requires_documents: bool,
        attachments: list[AttachmentResponse],
        approval_history: list[ApprovalHistoryEntry],
        payout_schedule: list[PayoutScheduleEntry],
    ) -> ClaimResponse:
        return cls(
            claim_id=claim.ClaimID,
            child_id=claim.ChildID,
            child_name=child_name,
            eligibility_id=claim.EligibilityID,
            invoice_date=claim.InvoiceDate,
            invoice_number=claim.InvoiceNumber,
            invoice_amount=claim.InvoiceAmount,
            claim_amount=claim.ClaimAmount,
            claim_status=claim.ClaimStatus,
            comments=claim.Comments,
            submitted_date=claim.SubmittedDate,
            created_date=claim.CreatedDate,
            requires_documents=requires_documents,
            attachments=attachments,
            approval_history=approval_history,
            payout_schedule=payout_schedule,
        )
