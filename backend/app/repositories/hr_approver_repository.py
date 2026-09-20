from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr_approver import HRApprover


def is_active_hr_approver(db: Session, employee_id: str) -> bool:
    row = db.execute(
        select(HRApprover).where(
            HRApprover.EmployeeID == employee_id,
            HRApprover.IsActive == True,  # noqa: E712 — see child_repository for why
        )
    ).scalar_one_or_none()
    return row is not None
