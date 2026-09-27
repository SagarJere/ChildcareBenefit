"""bulk add children history

Revision ID: a2c6f8e0d174
Revises: f19b6d3c8a47
Create Date: 2026-09-26 12:00:00.000000

Adds Childcare_BulkAddChildrenBatch / Childcare_BulkAddChildrenRow (user
direction 2026-09-26): a permanent audit trail of every HR bulk-add-
children *commit* attempt (never preview, since that never persists
anything), so a later dispute ("I uploaded 2, only 1 was added") can be
settled by pointing at exactly what happened to each row and why.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c6f8e0d174'
down_revision: Union[str, None] = 'f19b6d3c8a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_BulkAddChildrenBatch",
        sa.Column("BulkUploadID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("UploadedBy", sa.String(length=50), nullable=False),
        sa.Column("UploadedFileName", sa.String(length=260), nullable=True),
        sa.Column("TotalRows", sa.Integer(), nullable=False),
        sa.Column("SucceededCount", sa.Integer(), nullable=False),
        sa.Column("FailedCount", sa.Integer(), nullable=False),
        sa.Column(
            "UploadedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("BulkUploadID"),
    )
    op.create_index(
        "IX_BulkAddChildrenBatch_UploadedBy_UploadedDate",
        "Childcare_BulkAddChildrenBatch",
        ["UploadedBy", "UploadedDate"],
    )

    op.create_table(
        "Childcare_BulkAddChildrenRow",
        sa.Column("BulkUploadRowID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("BulkUploadID", sa.Integer(), nullable=False),
        sa.Column("RowNumber", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=50), nullable=False),
        sa.Column("ChildName", sa.String(length=200), nullable=False),
        sa.Column("ChildDOBRaw", sa.String(length=50), nullable=False),
        sa.Column("Status", sa.String(length=20), nullable=False),
        sa.Column("Message", sa.String(length=500), nullable=True),
        # Must match Childcare_ChildMaster.ChildID's real length (VARCHAR(30),
        # verified via INFORMATION_SCHEMA) — SQL Server requires exact
        # length/scale match between FK and referenced columns.
        sa.Column("ChildID", sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint("BulkUploadRowID"),
        sa.ForeignKeyConstraint(
            ["BulkUploadID"],
            ["Childcare_BulkAddChildrenBatch.BulkUploadID"],
            name="FK_BulkAddChildrenRow_Batch",
        ),
        sa.ForeignKeyConstraint(
            ["ChildID"],
            ["Childcare_ChildMaster.ChildID"],
            name="FK_BulkAddChildrenRow_Child",
        ),
    )
    op.create_index(
        "IX_BulkAddChildrenRow_BulkUploadID",
        "Childcare_BulkAddChildrenRow",
        ["BulkUploadID"],
    )
    op.create_index(
        "IX_BulkAddChildrenRow_EmployeeID",
        "Childcare_BulkAddChildrenRow",
        ["EmployeeID"],
    )


def downgrade() -> None:
    op.drop_index("IX_BulkAddChildrenRow_EmployeeID", table_name="Childcare_BulkAddChildrenRow")
    op.drop_index("IX_BulkAddChildrenRow_BulkUploadID", table_name="Childcare_BulkAddChildrenRow")
    op.drop_table("Childcare_BulkAddChildrenRow")
    op.drop_index(
        "IX_BulkAddChildrenBatch_UploadedBy_UploadedDate",
        table_name="Childcare_BulkAddChildrenBatch",
    )
    op.drop_table("Childcare_BulkAddChildrenBatch")
