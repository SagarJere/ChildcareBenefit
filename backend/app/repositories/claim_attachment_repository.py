from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.claim_attachment import ClaimAttachment


def get_for_claim(db: Session, claim_id: int) -> list[ClaimAttachment]:
    return list(
        db.execute(
            select(ClaimAttachment)
            .where(ClaimAttachment.ClaimID == claim_id)
            .order_by(ClaimAttachment.UploadedDate)
        )
        .scalars()
        .all()
    )


def get_attachment_for_claim(
    db: Session, claim_id: int, attachment_id: int
) -> ClaimAttachment | None:
    return db.execute(
        select(ClaimAttachment).where(
            ClaimAttachment.ClaimID == claim_id, ClaimAttachment.AttachmentID == attachment_id
        )
    ).scalar_one_or_none()


def delete_for_claim(db: Session, claim_id: int) -> None:
    """The underlying MinIO objects are deliberately left in place — a
    harmless orphan, same tolerance already applied elsewhere in this
    module when a DB write fails after a successful upload."""
    db.execute(delete(ClaimAttachment).where(ClaimAttachment.ClaimID == claim_id))


def create_attachment(
    db: Session,
    *,
    claim_id: int,
    attachment_type: str,
    original_file_name: str,
    stored_file_name: str,
    bucket_name: str,
    object_key: str,
    content_type: str,
    file_size: int,
    uploaded_by: str,
) -> ClaimAttachment:
    attachment = ClaimAttachment(
        ClaimID=claim_id,
        AttachmentType=attachment_type,
        OriginalFileName=original_file_name,
        StoredFileName=stored_file_name,
        BucketName=bucket_name,
        ObjectKey=object_key,
        ContentType=content_type,
        FileSize=file_size,
        UploadedBy=uploaded_by,
    )
    db.add(attachment)
    db.flush()
    return attachment
