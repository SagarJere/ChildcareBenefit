from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.payout_settings import PayoutSettings
    from app.models.payout_settings_history import PayoutSettingsHistory


class PayoutSettingsResponse(BaseModel):
    submission_cutoff_day: int
    claims_blocked: bool
    open_financial_year: str | None
    force_same_month_payout: bool
    updated_by: str | None
    updated_date: datetime | None

    @classmethod
    def from_orm_model(cls, settings: PayoutSettings) -> PayoutSettingsResponse:
        return cls(
            submission_cutoff_day=settings.SubmissionCutoffDay,
            claims_blocked=settings.ClaimsBlocked,
            open_financial_year=settings.OpenFinancialYear,
            force_same_month_payout=settings.ForceSameMonthPayout,
            updated_by=settings.UpdatedBy,
            updated_date=settings.UpdatedDate,
        )


class PayoutSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Capped at 28 so the cutoff day exists in every month (see
    # DECISIONS_LOG.md) — no need to special-case Feb or 30-day months.
    submission_cutoff_day: int = Field(ge=1, le=28)
    claims_blocked: bool
    force_same_month_payout: bool


class PayoutSettingsHistoryEntry(BaseModel):
    changed_by: str
    previous_submission_cutoff_day: int
    new_submission_cutoff_day: int
    previous_claims_blocked: bool
    new_claims_blocked: bool
    previous_open_financial_year: str | None
    new_open_financial_year: str | None
    previous_force_same_month_payout: bool
    new_force_same_month_payout: bool
    changed_date: datetime

    @classmethod
    def from_orm_model(cls, entry: PayoutSettingsHistory) -> PayoutSettingsHistoryEntry:
        return cls(
            changed_by=entry.ChangedBy,
            previous_submission_cutoff_day=entry.PreviousSubmissionCutoffDay,
            new_submission_cutoff_day=entry.NewSubmissionCutoffDay,
            previous_claims_blocked=entry.PreviousClaimsBlocked,
            new_claims_blocked=entry.NewClaimsBlocked,
            previous_open_financial_year=entry.PreviousOpenFinancialYear,
            new_open_financial_year=entry.NewOpenFinancialYear,
            previous_force_same_month_payout=entry.PreviousForceSameMonthPayout,
            new_force_same_month_payout=entry.NewForceSameMonthPayout,
            changed_date=entry.ChangedDate,
        )
