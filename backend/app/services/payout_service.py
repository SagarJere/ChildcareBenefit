"""Persists the payout calculation for one child's one financial year.

Per PAYOUT_REQUIREMENTS.md §7 (DECISIONS_LOG.md items 44-49): recompute is
always a full rebuild, triggered only when a new claim is approved for
that EligibilityID (Approved is terminal — see item 46 — so there is
nothing to unwind, only new approvals to layer on top of the existing
ones, in approval-time order).
"""
from sqlalchemy.orm import Session

from app.repositories import eligibility_repository, payout_repository
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

    approved_claims = payout_repository.get_approved_claims_with_approval_time(db, eligibility_id)

    result = payout_calculator.calculate_payout_schedule(
        eligibility_start_date=eligibility.EligibilityStartDate,
        eligibility_end_date=eligibility.EligibilityEndDate,
        approved_claims=approved_claims,
    )

    payout_repository.replace_ledger_and_allocations(
        db,
        eligibility=eligibility,
        ledger_entries=result.ledger,
        allocation_entries=result.allocations,
    )
