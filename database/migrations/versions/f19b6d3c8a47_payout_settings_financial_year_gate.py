"""payout settings financial year gate

Revision ID: f19b6d3c8a47
Revises: e5f7a2b8c913
Create Date: 2026-09-25 18:00:00.000000

Adds two HR-configurable controls to Childcare_PayoutSettings (user
direction 2026-09-25):

- OpenFinancialYearID/OpenFinancialYear: the last financial year that
  employees may raise/submit claims against. Left NULL by this
  migration — no raw-SQL backfill here, since Childcare_PayoutSettings
  is a lazily-created singleton (item 71's "no migration-seeded data to
  keep in sync" principle) that may not even have a row yet at migration
  time. Instead, payout_settings_repository.get_settings bootstraps it
  to *today's* FY, exactly once, the first time the row is ever read
  after this migration — see that function's own comment. This is a
  one-time bootstrap only, not an ongoing safety net: confirmed with the
  user that HR must explicitly open every FY from then on, including the
  very next calendar rollover, so close-out (e.g. March) can be held
  shut deliberately.
- ForceSameMonthPayout: an HR override for the financial-year close-out
  crunch — defaults to off, matching current behavior exactly until HR
  turns it on.

Also extends Childcare_PayoutSettingsHistory with matching before/after
columns, mirroring the existing audit trail for the other two settings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f19b6d3c8a47'
down_revision: Union[str, None] = 'e5f7a2b8c913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Childcare_PayoutSettings",
        sa.Column("OpenFinancialYearID", sa.Integer(), nullable=True),
    )
    op.add_column(
        "Childcare_PayoutSettings",
        sa.Column("OpenFinancialYear", sa.String(length=20), nullable=True),
    )
    op.create_foreign_key(
        "FK_PayoutSettings_OpenFinancialYear",
        "Childcare_PayoutSettings",
        "Childcare_FinancialYearMaster",
        ["OpenFinancialYearID"],
        ["FinancialYearID"],
    )
    op.add_column(
        "Childcare_PayoutSettings",
        sa.Column(
            "ForceSameMonthPayout", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.add_column(
        "Childcare_PayoutSettingsHistory",
        sa.Column("PreviousOpenFinancialYear", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "Childcare_PayoutSettingsHistory",
        sa.Column("NewOpenFinancialYear", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "Childcare_PayoutSettingsHistory",
        sa.Column(
            "PreviousForceSameMonthPayout",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "Childcare_PayoutSettingsHistory",
        sa.Column(
            "NewForceSameMonthPayout", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("Childcare_PayoutSettingsHistory", "NewForceSameMonthPayout")
    op.drop_column("Childcare_PayoutSettingsHistory", "PreviousForceSameMonthPayout")
    op.drop_column("Childcare_PayoutSettingsHistory", "NewOpenFinancialYear")
    op.drop_column("Childcare_PayoutSettingsHistory", "PreviousOpenFinancialYear")

    op.drop_column("Childcare_PayoutSettings", "ForceSameMonthPayout")
    op.drop_constraint(
        "FK_PayoutSettings_OpenFinancialYear", "Childcare_PayoutSettings", type_="foreignkey"
    )
    op.drop_column("Childcare_PayoutSettings", "OpenFinancialYear")
    op.drop_column("Childcare_PayoutSettings", "OpenFinancialYearID")
