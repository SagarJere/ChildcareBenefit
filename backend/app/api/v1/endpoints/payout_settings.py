from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_employee, get_current_hr_approver
from app.schemas.employee import EmployeeProfile
from app.schemas.payout_settings import (
    PayoutSettingsHistoryEntry,
    PayoutSettingsResponse,
    PayoutSettingsUpdateRequest,
)
from app.services import payout_settings_service

router = APIRouter()


@router.get("/payout-settings", response_model=PayoutSettingsResponse)
def get_payout_settings(
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> PayoutSettingsResponse:
    """Readable by any authenticated employee (not just HR) — the Raise
    Claim page uses this to show the current cutoff day and whether
    claims are paused, before the employee even tries to submit."""
    return payout_settings_service.get_settings(db)


@router.put("/hr/payout-settings", response_model=PayoutSettingsResponse)
def update_payout_settings(
    payload: PayoutSettingsUpdateRequest,
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> PayoutSettingsResponse:
    return payout_settings_service.update_settings(
        db, payload, updated_by=current_hr_employee.employee_id
    )


@router.get("/hr/payout-settings/history", response_model=list[PayoutSettingsHistoryEntry])
def get_payout_settings_history(
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[PayoutSettingsHistoryEntry]:
    return payout_settings_service.get_history(db)


@router.post("/hr/payout-settings/open-next-financial-year", response_model=PayoutSettingsResponse)
def open_next_financial_year(
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> PayoutSettingsResponse:
    """Advances the open financial year by exactly one, relative to
    whatever is currently open — see payout_settings_service.
    open_next_financial_year's own comment for why "next" is anchored
    there rather than to today's real calendar FY."""
    return payout_settings_service.open_next_financial_year(
        db, updated_by=current_hr_employee.employee_id
    )
