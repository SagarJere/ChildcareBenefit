"""HR-configurable global claim-processing settings (user direction
2026-09-25): the submission cutoff day that determines which month a
claim's payout lands in (see payout_calculator.py), a blanket
claims-blocked kill switch enforced in claim_service.create_claim/
submit_claim, and (added 2026-09-25, same day) the financial-year gate
enforced in claim_service._resolve_eligibility_for_invoice — see
is_financial_year_open and open_next_financial_year below. The
same-month-payout override for FY close-out is this same feature's
follow-up increment (payout_calculator.py), not covered here.

Every actual change is also recorded to Childcare_PayoutSettingsHistory
(user direction 2026-09-25, same day — a no-op save, e.g. re-submitting
identical values, writes no history row).
"""
from sqlalchemy.orm import Session

from app.repositories import financial_year_repository, payout_settings_repository
from app.schemas.payout_settings import (
    PayoutSettingsHistoryEntry,
    PayoutSettingsResponse,
    PayoutSettingsUpdateRequest,
)
from app.services import eligibility_calculator
from app.services.eligibility_calculator import FinancialYearWindow


def get_settings(db: Session) -> PayoutSettingsResponse:
    settings = payout_settings_repository.get_settings(db)
    return PayoutSettingsResponse.from_orm_model(settings)


def update_settings(
    db: Session, payload: PayoutSettingsUpdateRequest, updated_by: str
) -> PayoutSettingsResponse:
    settings = payout_settings_repository.get_settings(db)
    previous_submission_cutoff_day = settings.SubmissionCutoffDay
    previous_claims_blocked = settings.ClaimsBlocked
    previous_force_same_month_payout = settings.ForceSameMonthPayout

    updated = payout_settings_repository.update_settings(
        db,
        settings,
        submission_cutoff_day=payload.submission_cutoff_day,
        claims_blocked=payload.claims_blocked,
        force_same_month_payout=payload.force_same_month_payout,
        updated_by=updated_by,
    )

    if (
        previous_submission_cutoff_day != payload.submission_cutoff_day
        or previous_claims_blocked != payload.claims_blocked
        or previous_force_same_month_payout != payload.force_same_month_payout
    ):
        payout_settings_repository.record_history(
            db,
            changed_by=updated_by,
            previous_submission_cutoff_day=previous_submission_cutoff_day,
            new_submission_cutoff_day=payload.submission_cutoff_day,
            previous_claims_blocked=previous_claims_blocked,
            new_claims_blocked=payload.claims_blocked,
            # This PUT never touches the open financial year — only
            # open_next_financial_year does — so it's unchanged here.
            previous_open_financial_year=updated.OpenFinancialYear,
            new_open_financial_year=updated.OpenFinancialYear,
            previous_force_same_month_payout=previous_force_same_month_payout,
            new_force_same_month_payout=payload.force_same_month_payout,
        )

    return PayoutSettingsResponse.from_orm_model(updated)


def open_next_financial_year(db: Session, *, updated_by: str) -> PayoutSettingsResponse:
    """Advances the open financial year to exactly one past whatever is
    *currently* open — not one past today's real calendar FY. This is
    deliberate (confirmed with the user 2026-09-25): there is no
    automatic "current FY" fallback in this feature, so "next" can only
    mean "next after what HR has already opened." In the normal case
    (HR opens each FY in its own turn) this is the same thing; if HR
    falls behind, repeated clicks catch up one year at a time rather
    than jumping straight to whatever year it happens to be today."""
    settings = payout_settings_repository.get_settings(db)
    previous_open_financial_year = settings.OpenFinancialYear
    # get_settings() guarantees this is set (bootstrapped on first read).
    assert settings.OpenFinancialYearID is not None
    currently_open_fy_row = financial_year_repository.get_by_id(db, settings.OpenFinancialYearID)
    assert currently_open_fy_row is not None
    currently_open_fy = FinancialYearWindow(
        label=currently_open_fy_row.FinancialYear,
        start_date=currently_open_fy_row.StartDate,
        end_date=currently_open_fy_row.EndDate,
    )

    next_fy = eligibility_calculator.next_financial_year_window(currently_open_fy)
    next_fy_row = financial_year_repository.get_or_create(db, next_fy)

    updated = payout_settings_repository.set_open_financial_year(
        db,
        settings,
        financial_year_id=next_fy_row.FinancialYearID,
        financial_year_label=next_fy_row.FinancialYear,
        updated_by=updated_by,
    )

    if previous_open_financial_year != next_fy_row.FinancialYear:
        payout_settings_repository.record_history(
            db,
            changed_by=updated_by,
            previous_submission_cutoff_day=updated.SubmissionCutoffDay,
            new_submission_cutoff_day=updated.SubmissionCutoffDay,
            previous_claims_blocked=updated.ClaimsBlocked,
            new_claims_blocked=updated.ClaimsBlocked,
            previous_open_financial_year=previous_open_financial_year,
            new_open_financial_year=next_fy_row.FinancialYear,
            previous_force_same_month_payout=updated.ForceSameMonthPayout,
            new_force_same_month_payout=updated.ForceSameMonthPayout,
        )

    return PayoutSettingsResponse.from_orm_model(updated)


def is_financial_year_open(db: Session, claim_fy: FinancialYearWindow) -> bool:
    """Whether a claim dated into `claim_fy` may be raised/submitted:
    whether it's at or before whatever financial year HR has most
    recently opened (see open_next_financial_year).

    Deliberately no "current calendar FY" fallback (confirmed with the
    user 2026-09-25): this is a real, explicit HR-controlled gate, not
    a computed one, precisely so HR can hold a new FY closed on purpose
    during close-out — including right through the calendar rollover —
    rather than it silently reopening itself. get_settings() bootstraps
    the open FY to today's real FY exactly once, the first time this
    row is ever read, purely so the feature doesn't block every claim
    in the app the instant it ships; every year after that is on HR."""
    settings = payout_settings_repository.get_settings(db)
    # Always set — get_settings() bootstraps it on first read.
    assert settings.OpenFinancialYearID is not None
    open_fy = financial_year_repository.get_by_id(db, settings.OpenFinancialYearID)
    assert open_fy is not None
    return claim_fy.start_date <= open_fy.StartDate


def get_history(db: Session) -> list[PayoutSettingsHistoryEntry]:
    rows = payout_settings_repository.get_history(db)
    return [PayoutSettingsHistoryEntry.from_orm_model(row) for row in rows]
