"""payout settings history

Revision ID: c4d8f61a9e02
Revises: a7c3e9f21b84
Create Date: 2026-09-25 15:00:00.000000

Adds Childcare_PayoutSettingsHistory (user direction 2026-09-25): an
audit trail of changes to Childcare_PayoutSettings, mirroring
Childcare_ClaimApprovalHistory's before/after shape. Written only when a
change actually happens, not on every save attempt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8f61a9e02'
down_revision: Union[str, None] = 'a7c3e9f21b84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_PayoutSettingsHistory",
        sa.Column("PayoutSettingsHistoryID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ChangedBy", sa.String(length=50), nullable=False),
        sa.Column("PreviousSubmissionCutoffDay", sa.Integer(), nullable=False),
        sa.Column("NewSubmissionCutoffDay", sa.Integer(), nullable=False),
        sa.Column("PreviousClaimsBlocked", sa.Boolean(), nullable=False),
        sa.Column("NewClaimsBlocked", sa.Boolean(), nullable=False),
        sa.Column(
            "ChangedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("PayoutSettingsHistoryID"),
    )
    op.create_index(
        "IX_PayoutSettingsHistory_ChangedDate",
        "Childcare_PayoutSettingsHistory",
        ["ChangedDate"],
    )


def downgrade() -> None:
    op.drop_index(
        "IX_PayoutSettingsHistory_ChangedDate", table_name="Childcare_PayoutSettingsHistory"
    )
    op.drop_table("Childcare_PayoutSettingsHistory")
