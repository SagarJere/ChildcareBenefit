from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

RECEIPT_INVOICE = "RECEIPT_INVOICE"
PAYMENT_PROOF = "PAYMENT_PROOF"


class ClaimAttachment(Base):
    __tablename__ = "Childcare_ClaimAttachments"
    __table_args__ = (Index("IX_ClaimAttachments_ClaimID", "ClaimID"),)

    AttachmentID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ClaimID: Mapped[int] = mapped_column(ForeignKey("Childcare_ClaimMaster.ClaimID"))
    AttachmentType: Mapped[str]
    OriginalFileName: Mapped[str]
    StoredFileName: Mapped[str]
    BucketName: Mapped[str]
    ObjectKey: Mapped[str]
    ContentType: Mapped[str]
    FileSize: Mapped[int]
    UploadedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
    UploadedBy: Mapped[str]
