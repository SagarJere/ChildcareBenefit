from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    institution_name: str = Field(min_length=1, max_length=200)
    from_date: date
    to_date: date
    comments: str | None = Field(default=None, max_length=1000)

    @field_validator("invoice_date")
    @classmethod
    def invoice_date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Invoice date cannot be in the future.")
        return value

    @model_validator(mode="after")
    def from_date_not_after_to_date(self) -> ClaimCreateRequest:
        if self.from_date > self.to_date:
            raise ValueError("From Date must be on or before To Date.")
        return self


class ClaimUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_date: date
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_amount: Decimal = Field(gt=0)
    institution_name: str = Field(min_length=1, max_length=200)
    from_date: date
    to_date: date
    comments: str | None = Field(default=None, max_length=1000)

    @field_validator("invoice_date")
    @classmethod
    def invoice_date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Invoice date cannot be in the future.")
        return value

    @model_validator(mode="after")
    def from_date_not_after_to_date(self) -> ClaimUpdateRequest:
        if self.from_date > self.to_date:
            raise ValueError("From Date must be on or before To Date.")
        return self


class ClaimResponse(BaseModel):
    claim_id: int
    child_id: str
    child_name: str
    eligibility_id: int
    invoice_date: date
    invoice_number: str
    invoice_amount: Decimal
    claim_amount: Decimal
    institution_name: str | None
    from_date: date | None
    to_date: date | None
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
            institution_name=claim.InstitutionName,
            from_date=claim.FromDate,
            to_date=claim.ToDate,
            claim_status=claim.ClaimStatus,
            comments=claim.Comments,
            submitted_date=claim.SubmittedDate,
            created_date=claim.CreatedDate,
            requires_documents=requires_documents,
            attachments=attachments,
            approval_history=approval_history,
            payout_schedule=payout_schedule,
        )
