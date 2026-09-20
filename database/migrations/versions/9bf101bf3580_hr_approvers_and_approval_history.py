"""hr approvers and approval history

Revision ID: 9bf101bf3580
Revises: 6c0a95c447c0
Create Date: 2026-09-19

Adds Childcare_HRApprovers (per user direction 2026-09-19: a dedicated
access-control table — only an EmployeeID present here with IsActive=1
may view/act on HR claim endpoints) and Childcare_ClaimApprovalHistory
(Increment 5).

Childcare_HRApprovers.EmployeeID is a plain unique/indexed column, not a
foreign key to Master_Emp_BasicInfo — that table still has no primary key
or unique constraint to reference (see DECISIONS_LOG.md item 14). The
table starts empty; no HR approver is seeded, since deciding who has HR
access is an organizational decision this migration must not guess.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9bf101bf3580"
down_revision: Union[str, None] = "6c0a95c447c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_HRApprovers",
        sa.Column("HRApproverID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.PrimaryKeyConstraint("HRApproverID"),
        sa.UniqueConstraint("EmployeeID", name="UQ_HRApprovers_EmployeeID"),
    )

    op.create_table(
        "Childcare_ClaimApprovalHistory",
        sa.Column("ApprovalHistoryID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ClaimID", sa.BigInteger(), nullable=False),
        sa.Column("ActionBy", sa.String(length=20), nullable=False),
        sa.Column("Action", sa.String(length=20), nullable=False),
        sa.Column("PreviousStatus", sa.String(length=20), nullable=False),
        sa.Column("NewStatus", sa.String(length=20), nullable=False),
        sa.Column("ApprovedAmount", sa.DECIMAL(18, 2), nullable=True),
        sa.Column("Remarks", sa.String(length=1000), nullable=True),
        sa.Column("ActionDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.PrimaryKeyConstraint("ApprovalHistoryID"),
        sa.ForeignKeyConstraint(
            ["ClaimID"], ["Childcare_ClaimMaster.ClaimID"], name="FK_ApprovalHistory_ClaimMaster"
        ),
        sa.CheckConstraint(
            "Action IN ('Approved', 'Rejected', 'SentBack')", name="CK_ApprovalHistory_Action"
        ),
    )
    op.create_index("IX_ApprovalHistory_ClaimID", "Childcare_ClaimApprovalHistory", ["ClaimID"])


def downgrade() -> None:
    op.drop_index("IX_ApprovalHistory_ClaimID", table_name="Childcare_ClaimApprovalHistory")
    op.drop_table("Childcare_ClaimApprovalHistory")
    op.drop_table("Childcare_HRApprovers")
