"""claim institution and service period

Revision ID: f1a4c8d9e623
Revises: d3f6a19b2c47
Create Date: 2026-09-24 12:00:00.000000

Adds Childcare_ClaimMaster.InstitutionName/FromDate/ToDate (user direction
2026-09-24). Descriptive fields only: FromDate/ToDate record the service
period an invoice covers (validated at the application layer against the
child's age in months — >= 14 months, <= 72 months), but neither field
changes which EligibilityID a claim posts against (still InvoiceDate) or
how payout is allocated (still HR approval time). Nullable — claims
created before this feature don't have them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a4c8d9e623'
down_revision: Union[str, None] = 'd3f6a19b2c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Childcare_ClaimMaster",
        sa.Column("InstitutionName", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "Childcare_ClaimMaster", sa.Column("FromDate", sa.Date(), nullable=True)
    )
    op.add_column(
        "Childcare_ClaimMaster", sa.Column("ToDate", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("Childcare_ClaimMaster", "ToDate")
    op.drop_column("Childcare_ClaimMaster", "FromDate")
    op.drop_column("Childcare_ClaimMaster", "InstitutionName")
