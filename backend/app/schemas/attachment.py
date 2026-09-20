from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.claim_attachment import ClaimAttachment

AttachmentType = Literal["RECEIPT_INVOICE", "PAYMENT_PROOF"]


class AttachmentResponse(BaseModel):
    attachment_id: int
    claim_id: int
    attachment_type: AttachmentType
    original_file_name: str
    content_type: str
    file_size: int
    uploaded_date: datetime

    @classmethod
    def from_orm_model(cls, attachment: ClaimAttachment) -> AttachmentResponse:
        return cls(
            attachment_id=attachment.AttachmentID,
            claim_id=attachment.ClaimID,
            attachment_type=attachment.AttachmentType,  # type: ignore[arg-type]
            original_file_name=attachment.OriginalFileName,
            content_type=attachment.ContentType,
            file_size=attachment.FileSize,
            uploaded_date=attachment.UploadedDate,
        )
