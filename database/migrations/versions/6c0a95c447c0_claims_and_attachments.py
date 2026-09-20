"""claims and attachments

Revision ID: 6c0a95c447c0
Revises: 60e49816f89c
Create Date: 2026-09-19

Adds Childcare_ClaimMaster and Childcare_ClaimAttachments (Increment 4).
Childcare_ClaimApprovalHistory is deliberately not created yet — it is
only written to by HR actions (Increment 5), which do not exist yet.

ClaimStatus's CHECK constraint lists the full workflow from
CODEX_MASTER_INSTRUCTIONS.md §9 (Draft -> Submitted -> HR Review ->
Approved/Rejected/SentBack) even though this increment's code only ever
sets Draft or Submitted — this defines the column's complete valid domain
now so Increment 5 does not need a follow-up migration just to widen it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c0a95c447c0"
down_revision: Union[str, None] = "60e49816f89c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_ClaimMaster",
        sa.Column("ClaimID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("MEmpID", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("ChildID", sa.String(length=30), nullable=False),
        sa.Column("EligibilityID", sa.BigInteger(), nullable=False),
        sa.Column("InvoiceDate", sa.Date(), nullable=False),
        sa.Column("InvoiceNumber", sa.String(length=50), nullable=False),
        sa.Column("InvoiceAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("ClaimAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("ClaimStatus", sa.String(length=20), nullable=False),
        sa.Column("SubmittedDate", sa.DateTime(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.Column("CreatedBy", sa.String(length=50), nullable=False),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("ClaimID"),
        sa.ForeignKeyConstraint(
            ["ChildID"], ["Childcare_ChildMaster.ChildID"], name="FK_ClaimMaster_ChildMaster"
        ),
        sa.ForeignKeyConstraint(
            ["EligibilityID"],
            ["Childcare_EligibilityMaster.EligibilityID"],
            name="FK_ClaimMaster_EligibilityMaster",
        ),
        sa.CheckConstraint(
            "ClaimStatus IN ('Draft', 'Submitted', 'HRReview', 'Approved', 'Rejected', 'SentBack')",
            name="CK_ClaimMaster_Status",
        ),
        sa.CheckConstraint("InvoiceAmount > 0", name="CK_ClaimMaster_InvoiceAmount_Positive"),
        sa.CheckConstraint("ClaimAmount > 0", name="CK_ClaimMaster_ClaimAmount_Positive"),
    )
    op.create_index("IX_ClaimMaster_MEmpID", "Childcare_ClaimMaster", ["MEmpID"])
    op.create_index("IX_ClaimMaster_ChildID", "Childcare_ClaimMaster", ["ChildID"])
    op.create_index("IX_ClaimMaster_ClaimStatus", "Childcare_ClaimMaster", ["ClaimStatus"])

    op.create_table(
        "Childcare_ClaimAttachments",
        sa.Column("AttachmentID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ClaimID", sa.BigInteger(), nullable=False),
        sa.Column("AttachmentType", sa.String(length=30), nullable=False),
        sa.Column("OriginalFileName", sa.String(length=255), nullable=False),
        sa.Column("StoredFileName", sa.String(length=255), nullable=False),
        sa.Column("BucketName", sa.String(length=100), nullable=False),
        sa.Column("ObjectKey", sa.String(length=500), nullable=False),
        sa.Column("ContentType", sa.String(length=100), nullable=False),
        sa.Column("FileSize", sa.BigInteger(), nullable=False),
        sa.Column("UploadedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.Column("UploadedBy", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("AttachmentID"),
        sa.ForeignKeyConstraint(
            ["ClaimID"], ["Childcare_ClaimMaster.ClaimID"], name="FK_ClaimAttachments_ClaimMaster"
        ),
        sa.CheckConstraint(
            "AttachmentType IN ('RECEIPT_INVOICE', 'PAYMENT_PROOF')",
            name="CK_ClaimAttachments_Type",
        ),
        sa.CheckConstraint("FileSize > 0", name="CK_ClaimAttachments_FileSize_Positive"),
    )
    op.create_index("IX_ClaimAttachments_ClaimID", "Childcare_ClaimAttachments", ["ClaimID"])


def downgrade() -> None:
    op.drop_index("IX_ClaimAttachments_ClaimID", table_name="Childcare_ClaimAttachments")
    op.drop_table("Childcare_ClaimAttachments")

    op.drop_index("IX_ClaimMaster_ClaimStatus", table_name="Childcare_ClaimMaster")
    op.drop_index("IX_ClaimMaster_ChildID", table_name="Childcare_ClaimMaster")
    op.drop_index("IX_ClaimMaster_MEmpID", table_name="Childcare_ClaimMaster")
    op.drop_table("Childcare_ClaimMaster")
