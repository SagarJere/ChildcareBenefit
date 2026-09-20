"""child management and eligibility

Revision ID: 60e49816f89c
Revises: 22746c6c584e
Create Date: 2026-09-19

Adds Childcare_FinancialYearMaster, Childcare_ChildMaster, and
Childcare_EligibilityMaster (Increment 3). `Master_Emp_BasicInfo` is
untouched — it has no primary key or unique constraint (verified
2026-09-19), so MEmpID columns here are plain indexed INT columns rather
than foreign keys (see ChildcareBenefit_Codex_Documentation/DECISIONS_LOG.md
item 14).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "60e49816f89c"
down_revision: Union[str, None] = "22746c6c584e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Childcare_FinancialYearMaster",
        sa.Column("FinancialYearID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("FinancialYear", sa.String(length=10), nullable=False),
        sa.Column("StartDate", sa.Date(), nullable=False),
        sa.Column("EndDate", sa.Date(), nullable=False),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.PrimaryKeyConstraint("FinancialYearID"),
        sa.UniqueConstraint("FinancialYear", name="UQ_FinancialYearMaster_FinancialYear"),
    )

    op.create_table(
        "Childcare_ChildMaster",
        sa.Column("ChildID", sa.String(length=30), nullable=False),
        sa.Column("MEmpID", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("ChildSequenceNo", sa.Integer(), nullable=False),
        sa.Column("ChildName", sa.String(length=200), nullable=False),
        sa.Column("ChildDOB", sa.Date(), nullable=False),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.Column("CreatedBy", sa.String(length=50), nullable=False),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("ChildID"),
        sa.UniqueConstraint(
            "MEmpID", "ChildSequenceNo", name="UQ_ChildMaster_Employee_Sequence"
        ),
        sa.CheckConstraint("ChildSequenceNo IN (1, 2)", name="CK_ChildMaster_SequenceNo"),
    )
    op.create_index("IX_ChildMaster_MEmpID", "Childcare_ChildMaster", ["MEmpID"])

    op.create_table(
        "Childcare_EligibilityMaster",
        sa.Column("EligibilityID", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("MEmpID", sa.Integer(), nullable=False),
        sa.Column("EmployeeID", sa.String(length=20), nullable=False),
        sa.Column("ChildID", sa.String(length=30), nullable=False),
        sa.Column("ChildName", sa.String(length=200), nullable=False),
        sa.Column("ChildDOB", sa.Date(), nullable=False),
        sa.Column("FinancialYearID", sa.Integer(), nullable=False),
        sa.Column("FinancialYear", sa.String(length=10), nullable=False),
        sa.Column("EligibilityStartDate", sa.Date(), nullable=False),
        sa.Column("EligibilityEndDate", sa.Date(), nullable=True),
        sa.Column("EligibleMonths", sa.Integer(), nullable=False),
        sa.Column("MonthlyBenefitAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("AllottedAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("UtilizedAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("ApprovedAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("InProgressAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("RemainingAmount", sa.DECIMAL(18, 2), nullable=False),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), server_default=sa.text("GETUTCDATE()"), nullable=False),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("EligibilityID"),
        sa.ForeignKeyConstraint(
            ["ChildID"], ["Childcare_ChildMaster.ChildID"], name="FK_Eligibility_ChildMaster"
        ),
        sa.ForeignKeyConstraint(
            ["FinancialYearID"],
            ["Childcare_FinancialYearMaster.FinancialYearID"],
            name="FK_Eligibility_FinancialYearMaster",
        ),
        sa.UniqueConstraint(
            "MEmpID", "ChildID", "FinancialYearID", name="UQ_Eligibility_Employee_Child_FY"
        ),
    )
    op.create_index("IX_EligibilityMaster_MEmpID", "Childcare_EligibilityMaster", ["MEmpID"])
    op.create_index("IX_EligibilityMaster_ChildID", "Childcare_EligibilityMaster", ["ChildID"])


def downgrade() -> None:
    op.drop_index("IX_EligibilityMaster_ChildID", table_name="Childcare_EligibilityMaster")
    op.drop_index("IX_EligibilityMaster_MEmpID", table_name="Childcare_EligibilityMaster")
    op.drop_table("Childcare_EligibilityMaster")

    op.drop_index("IX_ChildMaster_MEmpID", table_name="Childcare_ChildMaster")
    op.drop_table("Childcare_ChildMaster")

    op.drop_table("Childcare_FinancialYearMaster")
