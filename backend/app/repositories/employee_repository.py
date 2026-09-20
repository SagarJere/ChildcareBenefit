import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import MasterEmpBasicInfo

logger = logging.getLogger(__name__)


def get_by_employee_id(db: Session, employee_id: str) -> MasterEmpBasicInfo | None:
    """Look up an employee by their business Employee ID.

    `Master_Emp_BasicInfo` currently has no unique constraint on
    `EmployeeID` (verified 2026-09-19), so more than one row could in
    theory match. If that ever happens it indicates a data-integrity
    problem in the employee master, not something this application can
    silently resolve, so it is logged and the first match (by internal
    MEmpID) is used deterministically.
    """
    rows = (
        db.execute(
            select(MasterEmpBasicInfo)
            .where(MasterEmpBasicInfo.EmployeeID == employee_id)
            .order_by(MasterEmpBasicInfo.MEmpID)
        )
        .scalars()
        .all()
    )

    if len(rows) > 1:
        logger.warning(
            "Multiple Master_Emp_BasicInfo rows found for EmployeeID=%s; "
            "using the row with the lowest MEmpID.",
            employee_id,
        )

    return rows[0] if rows else None


def get_all_active(db: Session) -> list[MasterEmpBasicInfo]:
    """Active employees with a usable EmployeeID, for the login page's
    autocomplete — see DECISIONS_LOG.md item 42. Ordered by name so the
    dropdown is easy to scan/search."""
    return list(
        db.execute(
            select(MasterEmpBasicInfo)
            .where(
                MasterEmpBasicInfo.IsActive == True,  # noqa: E712
                MasterEmpBasicInfo.EmployeeID.is_not(None),
            )
            .order_by(MasterEmpBasicInfo.FullName)
        )
        .scalars()
        .all()
    )


def get_names_by_employee_ids(db: Session, employee_ids: list[str]) -> dict[str, str]:
    """Bulk name lookup for reports, to avoid one query per row.

    Falls back to the EmployeeID itself for any ID with no FullName on
    file (or no matching row) — the same fallback used elsewhere.
    """
    if not employee_ids:
        return {}

    rows = db.execute(
        select(MasterEmpBasicInfo).where(MasterEmpBasicInfo.EmployeeID.in_(set(employee_ids)))
    ).scalars()

    names: dict[str, str] = {}
    for row in rows:
        if row.EmployeeID and row.EmployeeID not in names:
            names[row.EmployeeID] = row.FullName or row.EmployeeID

    return {emp_id: names.get(emp_id, emp_id) for emp_id in employee_ids}
