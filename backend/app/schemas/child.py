from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.eligibility import EligibilityResponse

if TYPE_CHECKING:
    from app.models.child import ChildMaster


class ChildDobMixin(BaseModel):
    child_dob: date

    @field_validator("child_dob")
    @classmethod
    def dob_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Child date of birth cannot be in the future.")
        return value


class ChildEligibilityPreviewRequest(ChildDobMixin):
    pass


class ChildCreateRequest(ChildDobMixin):
    model_config = ConfigDict(str_strip_whitespace=True)

    child_name: str = Field(min_length=1, max_length=200)


class ChildResponse(BaseModel):
    child_id: str
    employee_id: str
    child_sequence_no: int
    child_name: str
    child_dob: date
    is_active: bool
    created_date: datetime
    eligibility: EligibilityResponse | None = None

    @classmethod
    def from_orm_model(
        cls, child: ChildMaster, eligibility: EligibilityResponse | None = None
    ) -> ChildResponse:
        return cls(
            child_id=child.ChildID,
            employee_id=child.EmployeeID,
            child_sequence_no=child.ChildSequenceNo,
            child_name=child.ChildName,
            child_dob=child.ChildDOB,
            is_active=child.IsActive,
            created_date=child.CreatedDate,
            eligibility=eligibility,
        )
