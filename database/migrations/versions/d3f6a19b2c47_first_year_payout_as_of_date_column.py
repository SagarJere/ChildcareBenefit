"""first year payout as of date column

Revision ID: d3f6a19b2c47
Revises: 4a9247cb63f1
Create Date: 2026-09-24 10:00:00.000000

Adds Childcare_EligibilityMaster.FirstYearPayoutAsOfDate — the date an
eligibility record was actually created, used to anchor first-year-payout
catch-up bundling (a child added after their birth month gets the missed
months' payout bundled into the month they were added, rather than paid
individually against months before the record existed). Nullable: existing
rows get no catch-up (the original one-month-at-a-time behavior).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f6a19b2c47'
down_revision: Union[str, None] = '4a9247cb63f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Childcare_EligibilityMaster",
        sa.Column("FirstYearPayoutAsOfDate", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("Childcare_EligibilityMaster", "FirstYearPayoutAsOfDate")
