"""claim submission cutoff day snapshot

Revision ID: e5f7a2b8c913
Revises: c4d8f61a9e02
Create Date: 2026-09-25 16:30:00.000000

Adds Childcare_ClaimMaster.SubmissionCutoffDayAtSubmission (user-reported
bug 2026-09-25): freezes the Childcare_PayoutSettings.SubmissionCutoffDay
that was actually in effect when a claim was (most recently) submitted,
so a later HR change to the cutoff day can never retroactively reclassify
which month an already-submitted claim's payout lands in.

Existing claims have no true historical record of what cutoff day was
"active" for them (the setting didn't always exist with this
granularity), so every already-submitted claim (SubmittedDate IS NOT
NULL) is backfilled to the original default cutoff day, 5 — user
direction 2026-09-25, confirmed as the recommended option when this
gap was raised. Claims never submitted (Draft) are left NULL, matching
SubmittedDate's own nullability, and get a real value the next time
they're actually submitted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f7a2b8c913'
down_revision: Union[str, None] = 'c4d8f61a9e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SUBMISSION_CUTOFF_DAY = 5


def upgrade() -> None:
    op.add_column(
        "Childcare_ClaimMaster",
        sa.Column("SubmissionCutoffDayAtSubmission", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE Childcare_ClaimMaster "
        "SET SubmissionCutoffDayAtSubmission = "
        f"{DEFAULT_SUBMISSION_CUTOFF_DAY} "
        "WHERE SubmittedDate IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("Childcare_ClaimMaster", "SubmissionCutoffDayAtSubmission")
