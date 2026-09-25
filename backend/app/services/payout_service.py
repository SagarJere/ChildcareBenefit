"""Persists the payout calculation for one child's one financial year.

Per PAYOUT_REQUIREMENTS.md §7 (DECISIONS_LOG.md items 44-49): recompute is
always a full rebuild, triggered only when a new claim is approved for
that EligibilityID (Approved is terminal — see item 46 — so there is
nothing to unwind, only new approvals to layer on top of the existing
ones, in effective-processing-month order — see payout_calculator.py).
"""
from sqlalchemy.orm import Session

from app.repositories import eligibility_repository, payout_repository, payout_settings_repository
from app.services import payout_calculator


def recalculate_payout(db: Session, eligibility_id: int) -> None:
    eligibility = eligibility_repository.get_by_id(db, eligibility_id)
    assert eligibility is not None
    if eligibility.EligibilityEndDate is None:
        # Zero eligible months (e.g. the child had already passed the
        # six-year cutoff before this financial year started) — nothing
        # to allocate, and a claim could never have been approved against
        # it anyway (RemainingAmount would be 0).
        return

    # Each claim already carries the cutoff day that was actually in
    # effect when it was submitted (ClaimMaster.
    # SubmissionCutoffDayAtSubmission, via ApprovedClaimInput.
    # submission_cutoff_day) — so this full rebuild naturally applies the
    # right historical cutoff to each claim, even if HR has changed the
    # setting one or more times since. See that field's own comment for
    # the bug this fixes: a single *current* setting applied to every
    # claim on every rebuild used to retroactively reclassify which month
    # an already-submitted claim's payout landed in.
    approved_claims = payout_repository.get_approved_claims_with_approval_time(db, eligibility_id)

    # Falls back to the window's own start date (i.e. no catch-up — each
    # first-year month stands alone) for eligibility rows created before
    # FirstYearPayoutAsOfDate existed (2026-09-24).
    first_year_payout_as_of_date = (
        eligibility.FirstYearPayoutAsOfDate or eligibility.EligibilityStartDate
    )
    # Unlike the cutoff day, this is read *live* on every rebuild rather
    # than snapshotted onto each claim — deliberately so (user direction
    # 2026-09-25): the whole point of this HR override is to sweep
    # everything currently in flight into the current month the moment
    # it's turned on, not just affect claims approved from then on. See
    # ForceSameMonthPayout's own comment on the model.
    force_same_month_payout = payout_settings_repository.get_settings(db).ForceSameMonthPayout
    result = payout_calculator.calculate_payout_schedule(
        child_dob=eligibility.ChildDOB,
        eligibility_start_date=eligibility.EligibilityStartDate,
        eligibility_end_date=eligibility.EligibilityEndDate,
        first_year_payout_as_of_date=first_year_payout_as_of_date,
        force_same_month_payout=force_same_month_payout,
        approved_claims=approved_claims,
    )

    payout_repository.replace_ledger_and_allocations(
        db,
        eligibility=eligibility,
        ledger_entries=result.ledger,
        allocation_entries=result.allocations,
    )
