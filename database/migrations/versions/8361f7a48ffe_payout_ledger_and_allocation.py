"""payout monthly ledger and allocation

Revision ID: 8361f7a48ffe
Revises: b6e682ad8a0d
Create Date: 2026-09-20

Adds Childcare_PayoutMonthlyLedger and Childcare_PayoutAllocation per
PAYOUT_REQUIREMENTS.md (finalized by user 2026-09-20; see
DECISIONS_LOG.md items 44-49). Both tables are purely derived/disposable
— fully deleted and regenerated for a given EligibilityID every time
`app/services/payout_service.recalculate_payout` runs (currently
triggered only by HR approving a claim). No LedgerStatus/AllocationStatus
columns for v1 (every row is always the current, fully-recomputed
state), and no UpdatedDate/UpdatedBy — rows are never individually
edited, only wholesale replaced, so CreatedDate alone (the timestamp of
the recompute that produced this row) is meaningful.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8361f7a48ffe"
down_revision: Union[str, None] = "b6e682ad8a0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_PayoutMonthlyLedger",
        sa.Column("PayoutLedgerID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("MEmpID", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("ChildID", sa.String(length=30), nullable=False),
        sa.Column("EligibilityID", sa.BigInteger(), nullable=False),
        sa.Column("FinancialYearID", sa.Integer(), nullable=False),
        sa.Column("FinancialYear", sa.String(length=10), nullable=False),
        sa.Column("PayoutMonth", sa.Date(), nullable=False),
        sa.Column("EntitlementAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("OpeningBalance", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("TotalAvailableAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("ClaimAllocatedAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("AdjustmentAmount", sa.DECIMAL(18, 2), nullable=False, server_default="0"),
        sa.Column("ClosingBalance", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("CalculatedPayoutAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.PrimaryKeyConstraint("PayoutLedgerID"),
        sa.ForeignKeyConstraint(
            ["ChildID"], ["Childcare_ChildMaster.ChildID"], name="FK_PayoutLedger_ChildMaster"
        ),
        sa.ForeignKeyConstraint(
            ["EligibilityID"],
            ["Childcare_EligibilityMaster.EligibilityID"],
            name="FK_PayoutLedger_EligibilityMaster",
        ),
        sa.ForeignKeyConstraint(
            ["FinancialYearID"],
            ["Childcare_FinancialYearMaster.FinancialYearID"],
            name="FK_PayoutLedger_FinancialYearMaster",
        ),
        sa.UniqueConstraint(
            "EligibilityID", "PayoutMonth", name="UQ_PayoutLedger_Eligibility_Month"
        ),
    )
    op.create_index(
        "IX_PayoutLedger_EligibilityID", "Childcare_PayoutMonthlyLedger", ["EligibilityID"]
    )
    op.create_index("IX_PayoutLedger_MEmpID", "Childcare_PayoutMonthlyLedger", ["MEmpID"])

    op.create_table(
        "Childcare_PayoutAllocation",
        sa.Column("PayoutAllocationID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ClaimID", sa.BigInteger(), nullable=False),
        sa.Column("PayoutLedgerID", sa.BigInteger(), nullable=False),
        sa.Column("MEmpID", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("ChildID", sa.String(length=30), nullable=False),
        sa.Column("EligibilityID", sa.BigInteger(), nullable=False),
        sa.Column("FinancialYearID", sa.Integer(), nullable=False),
        sa.Column("PayoutMonth", sa.Date(), nullable=False),
        sa.Column("AllocationSequence", sa.Integer(), nullable=False),
        sa.Column("AllocatedAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.PrimaryKeyConstraint("PayoutAllocationID"),
        sa.ForeignKeyConstraint(
            ["ClaimID"], ["Childcare_ClaimMaster.ClaimID"], name="FK_PayoutAllocation_ClaimMaster"
        ),
        sa.ForeignKeyConstraint(
            ["PayoutLedgerID"],
            ["Childcare_PayoutMonthlyLedger.PayoutLedgerID"],
            name="FK_PayoutAllocation_PayoutLedger",
        ),
        sa.ForeignKeyConstraint(
            ["EligibilityID"],
            ["Childcare_EligibilityMaster.EligibilityID"],
            name="FK_PayoutAllocation_EligibilityMaster",
        ),
    )
    op.create_index("IX_PayoutAllocation_ClaimID", "Childcare_PayoutAllocation", ["ClaimID"])
    op.create_index(
        "IX_PayoutAllocation_EligibilityID", "Childcare_PayoutAllocation", ["EligibilityID"]
    )
    op.create_index(
        "IX_PayoutAllocation_PayoutLedgerID", "Childcare_PayoutAllocation", ["PayoutLedgerID"]
    )


def downgrade() -> None:
    op.drop_index("IX_PayoutAllocation_PayoutLedgerID", table_name="Childcare_PayoutAllocation")
    op.drop_index("IX_PayoutAllocation_EligibilityID", table_name="Childcare_PayoutAllocation")
    op.drop_index("IX_PayoutAllocation_ClaimID", table_name="Childcare_PayoutAllocation")
    op.drop_table("Childcare_PayoutAllocation")
    op.drop_index("IX_PayoutLedger_MEmpID", table_name="Childcare_PayoutMonthlyLedger")
    op.drop_index("IX_PayoutLedger_EligibilityID", table_name="Childcare_PayoutMonthlyLedger")
    op.drop_table("Childcare_PayoutMonthlyLedger")
