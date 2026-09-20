"""baseline

Revision ID: 22746c6c584e
Revises:
Create Date: 2026-09-19

This is an intentionally empty baseline revision. It establishes the
Alembic version-tracking table for the Childcare Benefit database without
creating any business tables. `Master_Emp_BasicInfo` already exists and is
owned outside this migration chain; Childcare_* business tables are added in
their own future increments once each feature is implemented.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "22746c6c584e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
