"""Employee profile schema returned by Login and /me.

Fields mirror the verified real columns of `Master_Emp_BasicInfo` — there is
no `Gender` field (see DATABASE_DESIGN.md).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.employee import MasterEmpBasicInfo


class EmployeeProfile(BaseModel):
    memp_id: int
    employee_id: str
    full_name: str | None
    my_single_id: str | None
    join_date: datetime | None
    # UX convenience only (e.g. showing/hiding the HR nav link) — backend
    # authorization for HR endpoints is enforced independently by
    # get_current_hr_approver on every request, never by this flag.
    is_hr_approver: bool = False

    @classmethod
    def from_orm_model(
        cls, employee: MasterEmpBasicInfo, *, is_hr_approver: bool = False
    ) -> EmployeeProfile:
        return cls(
            memp_id=employee.MEmpID,
            employee_id=employee.EmployeeID or "",
            full_name=employee.FullName,
            my_single_id=employee.MySingleID,
            join_date=employee.Joindate,
            is_hr_approver=is_hr_approver,
        )


class ActiveEmployeeOption(BaseModel):
    """One entry in the login page's employee autocomplete — deliberately
    minimal (no join date, MySingleID, etc.), see DECISIONS_LOG.md item 42."""

    employee_id: str
    full_name: str | None

    @classmethod
    def from_orm_model(cls, employee: MasterEmpBasicInfo) -> ActiveEmployeeOption:
        return cls(employee_id=employee.EmployeeID or "", full_name=employee.FullName)
