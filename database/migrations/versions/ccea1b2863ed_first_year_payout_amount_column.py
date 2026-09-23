"""first year payout amount column

Revision ID: ccea1b2863ed
Revises: 8361f7a48ffe
Create Date: 2026-09-23 20:54:16.231748

Adds Childcare_PayoutMonthlyLedger.FirstYearPayoutAmount: the child's
first 13 months of life are auto-paid with no claim involved (user
direction 2026-09-22), mutually exclusive per month with the existing
ClaimAllocatedAmount. Childcare_PayoutAllocation is untouched — there is
no claim behind a first-year month to allocate. This table is purely
derived (see the original payout migration's docstring), so a
NOT NULL column with a default of 0 is safe to add even with existing
rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccea1b2863ed'
down_revision: Union[str, None] = '8361f7a48ffe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Childcare_PayoutMonthlyLedger",
        sa.Column(
            "FirstYearPayoutAmount", sa.DECIMAL(18, 2), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("Childcare_PayoutMonthlyLedger", "FirstYearPayoutAmount")
