from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

DEFAULT_SUBMISSION_CUTOFF_DAY = 5


class PayoutSettings(Base):
    """A single-row table (see payout_settings_repository.get_settings,
    which creates the row on first read rather than relying on a seeded
    migration) holding HR-configurable, global claim-processing settings
    (user direction 2026-09-25):

    - SubmissionCutoffDay: a claim submitted on or before this day of the
      month is eligible for that same month's payout; submitted later,
      payout is pushed to the next month regardless of how quickly it's
      approved — see payout_calculator.py.
    - ClaimsBlocked: an HR-controlled kill switch that stops employees
      from creating or submitting claims at all, independent of the
      cutoff day (e.g. during month-end processing) — see
      claim_service.create_claim/submit_claim. HR's own review actions
      (approve/reject/send-back) are deliberately unaffected.
    - OpenFinancialYearID/OpenFinancialYear (user direction 2026-09-25):
      the last financial year that employees may raise/submit claims
      against. Deliberately NOT reset automatically at each year's
      calendar rollover — HR must explicitly open even the very next FY
      (see payout_settings_service.open_next_financial_year), including
      right as it starts, or claim submission blocks entirely for that
      FY until they do. This is intentional, confirmed with the user:
      the whole point is to let HR hold the gate shut during FY close-
      out (e.g. March) and open it deliberately when ready, not to fall
      back to some automatic "current FY" safety net. Bootstrapped to
      *today's* FY the first time this row is ever read (see
      payout_settings_repository.get_settings) purely so the feature
      doesn't immediately block every claim in the app the moment it
      ships — after that one-time bootstrap, it only ever changes via
      an explicit HR action. FinancialYear is denormalized (mirroring
      EligibilityMaster.FinancialYear) purely for display without a
      join; the ID is what comparisons use.
    - ForceSameMonthPayout: an HR-controlled override for the financial-
      year close-out crunch (e.g. March) — while on, every approval pays
      out in its own approval month, ignoring the submission-cutoff-day
      deferral rule entirely (see payout_calculator.py). Unlike
      SubmissionCutoffDay, this is read fresh at every recompute, not
      snapshotted onto the claim: the point is to sweep everything
      currently in flight into the current month immediately once HR
      turns it on, not just affect future submissions.
    """

    __tablename__ = "Childcare_PayoutSettings"

    PayoutSettingID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    SubmissionCutoffDay: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_SUBMISSION_CUTOFF_DAY
    )
    ClaimsBlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    OpenFinancialYearID: Mapped[int | None] = mapped_column(
        ForeignKey("Childcare_FinancialYearMaster.FinancialYearID"), nullable=True
    )
    OpenFinancialYear: Mapped[str | None] = mapped_column(nullable=True)
    ForceSameMonthPayout: Mapped[bool] = mapped_column(Boolean, default=False)
    UpdatedBy: Mapped[str | None] = mapped_column(nullable=True)
    UpdatedDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
