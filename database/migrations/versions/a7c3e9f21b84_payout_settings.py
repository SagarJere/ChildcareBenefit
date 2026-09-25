"""payout settings

Revision ID: a7c3e9f21b84
Revises: f1a4c8d9e623
Create Date: 2026-09-25 09:00:00.000000

Adds Childcare_PayoutSettings (user direction 2026-09-25): a single-row
table for two HR-configurable, global claim-processing settings —
SubmissionCutoffDay (a claim submitted after this day of the month has
its payout pushed to the next month, regardless of approval speed) and
ClaimsBlocked (an HR kill switch stopping all new claim creation/
submission). The row itself is created lazily on first read by
payout_settings_repository.get_settings, not seeded here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e9f21b84'
down_revision: Union[str, None] = 'f1a4c8d9e623'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_PayoutSettings",
        sa.Column("PayoutSettingID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("SubmissionCutoffDay", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "ClaimsBlocked", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("UpdatedBy", sa.String(length=50), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column(
            "CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("PayoutSettingID"),
    )


def downgrade() -> None:
    op.drop_table("Childcare_PayoutSettings")
