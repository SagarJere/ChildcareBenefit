from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.child import ChildMaster

MAX_CHILDREN_PER_EMPLOYEE = 2
VALID_SEQUENCE_NUMBERS = (1, 2)


def get_active_children(db: Session, memp_id: int) -> list[ChildMaster]:
    # `.is_(True)` compiles to the invalid `IS 1` on the MSSQL dialect —
    # `== True` (a SQLAlchemy column comparison, not a Python bool check)
    # correctly compiles to `= 1`.
    return list(
        db.execute(
            select(ChildMaster)
            .where(ChildMaster.MEmpID == memp_id, ChildMaster.IsActive == True)  # noqa: E712
            .order_by(ChildMaster.ChildSequenceNo)
        )
        .scalars()
        .all()
    )


def get_child_for_employee(db: Session, memp_id: int, child_id: str) -> ChildMaster | None:
    return db.execute(
        select(ChildMaster).where(
            ChildMaster.MEmpID == memp_id,
            ChildMaster.ChildID == child_id,
            ChildMaster.IsActive == True,  # noqa: E712
        )
    ).scalar_one_or_none()


def get_child_by_id(db: Session, child_id: str) -> ChildMaster | None:
    """Unscoped lookup (no employee/active filter) for internal use once a
    caller has already established ownership through another path — e.g.
    a claim's ChildID, where ownership is enforced via the claim's own
    MEmpID rather than by re-checking the child here."""
    return db.execute(
        select(ChildMaster).where(ChildMaster.ChildID == child_id)
    ).scalar_one_or_none()


def get_all_active_children(db: Session) -> list[ChildMaster]:
    """Unscoped (across all employees) — for HR reports only."""
    return list(
        db.execute(
            select(ChildMaster).where(ChildMaster.IsActive == True)  # noqa: E712
        )
        .scalars()
        .all()
    )


def next_sequence_number(existing_children: list[ChildMaster]) -> int:
    used = {child.ChildSequenceNo for child in existing_children}
    for candidate in VALID_SEQUENCE_NUMBERS:
        if candidate not in used:
            return candidate
    raise RuntimeError("No available child sequence number (should be unreachable).")


def create_child(
    db: Session,
    *,
    child_id: str,
    memp_id: int,
    employee_id: str,
    sequence_no: int,
    child_name: str,
    child_dob: date,
    created_by: str,
) -> ChildMaster:
    child = ChildMaster(
        ChildID=child_id,
        MEmpID=memp_id,
        EmployeeID=employee_id,
        ChildSequenceNo=sequence_no,
        ChildName=child_name,
        ChildDOB=child_dob,
        IsActive=True,
        CreatedBy=created_by,
    )
    db.add(child)
    db.flush()
    return child
