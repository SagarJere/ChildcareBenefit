"""child employee name dob unique constraint

Revision ID: 4a9247cb63f1
Revises: ccea1b2863ed
Create Date: 2026-09-23 21:52:05.211782

Backstop against a duplicate add-child submission (a slow response makes
the first attempt look hung, the user resubmits, and both succeed as two
separate children with the same name/DOB) — see DECISIONS_LOG.md.
child_service.add_child already checks for this before inserting; this
constraint guarantees it even under a genuine race between two
concurrent requests.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a9247cb63f1'
down_revision: Union[str, None] = 'ccea1b2863ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "UQ_ChildMaster_Employee_Name_DOB",
        "Childcare_ChildMaster",
        ["MEmpID", "ChildName", "ChildDOB"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "UQ_ChildMaster_Employee_Name_DOB", "Childcare_ChildMaster", type_="unique"
    )
