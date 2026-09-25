from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payout_settings import PayoutSettings
from app.models.payout_settings_history import PayoutSettingsHistory
from app.repositories import financial_year_repository
from app.services import eligibility_calculator


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_settings(db: Session) -> PayoutSettings:
    """The single settings row, created on first read with defaults if it
    doesn't exist yet — no migration-seeded data to keep in sync. A rare
    concurrent first-read racing to create two rows is harmless here (a
    global settings singleton, not financial data): callers always order
    by PayoutSettingID, so the same row is deterministically used either
    way, and this is unlike the child/claim/approval races elsewhere in
    this codebase that actually caused production incidents."""
    settings = db.execute(
        select(PayoutSettings).order_by(PayoutSettings.PayoutSettingID)
    ).scalars().first()
    if settings is None:
        settings = PayoutSettings()
        db.add(settings)
        db.flush()

    if settings.OpenFinancialYearID is None:
        _bootstrap_open_financial_year(db, settings)

    return settings


def _bootstrap_open_financial_year(db: Session, settings: PayoutSettings) -> None:
    """One-time bootstrap (user direction 2026-09-25) so the financial-
    year gate doesn't immediately block every claim in the app the
    moment this feature ships, or the instant a brand-new settings row
    is first created: sets the open FY to *today's* real FY, exactly
    once. From then on this column only ever changes via
    payout_settings_service.open_next_financial_year — confirmed with
    the user there is deliberately no ongoing "current FY" fallback
    after this, including at the next calendar rollover."""
    current_fy = eligibility_calculator.compute_financial_year(date.today())
    row = financial_year_repository.get_or_create(db, current_fy)
    settings.OpenFinancialYearID = row.FinancialYearID
    settings.OpenFinancialYear = row.FinancialYear
    db.flush()


def update_settings(
    db: Session,
    settings: PayoutSettings,
    *,
    submission_cutoff_day: int,
    claims_blocked: bool,
    force_same_month_payout: bool,
    updated_by: str,
) -> PayoutSettings:
    settings.SubmissionCutoffDay = submission_cutoff_day
    settings.ClaimsBlocked = claims_blocked
    settings.ForceSameMonthPayout = force_same_month_payout
    settings.UpdatedBy = updated_by
    settings.UpdatedDate = _utc_now_naive()
    db.flush()
    return settings


def set_open_financial_year(
    db: Session,
    settings: PayoutSettings,
    *,
    financial_year_id: int,
    financial_year_label: str,
    updated_by: str,
) -> PayoutSettings:
    settings.OpenFinancialYearID = financial_year_id
    settings.OpenFinancialYear = financial_year_label
    settings.UpdatedBy = updated_by
    settings.UpdatedDate = _utc_now_naive()
    db.flush()
    return settings


def record_history(
    db: Session,
    *,
    changed_by: str,
    previous_submission_cutoff_day: int,
    new_submission_cutoff_day: int,
    previous_claims_blocked: bool,
    new_claims_blocked: bool,
    previous_open_financial_year: str | None,
    new_open_financial_year: str | None,
    previous_force_same_month_payout: bool,
    new_force_same_month_payout: bool,
) -> PayoutSettingsHistory:
    entry = PayoutSettingsHistory(
        ChangedBy=changed_by,
        PreviousSubmissionCutoffDay=previous_submission_cutoff_day,
        NewSubmissionCutoffDay=new_submission_cutoff_day,
        PreviousClaimsBlocked=previous_claims_blocked,
        NewClaimsBlocked=new_claims_blocked,
        PreviousOpenFinancialYear=previous_open_financial_year,
        NewOpenFinancialYear=new_open_financial_year,
        PreviousForceSameMonthPayout=previous_force_same_month_payout,
        NewForceSameMonthPayout=new_force_same_month_payout,
    )
    db.add(entry)
    db.flush()
    return entry


def get_history(db: Session, *, limit: int = 50) -> list[PayoutSettingsHistory]:
    return list(
        db.execute(
            select(PayoutSettingsHistory)
            .order_by(PayoutSettingsHistory.ChangedDate.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
