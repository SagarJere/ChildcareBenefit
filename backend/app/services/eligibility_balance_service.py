"""Keeps Childcare_EligibilityMaster's ApprovedAmount/UtilizedAmount/
InProgressAmount/RemainingAmount in sync with real claim activity.

Per user direction 2026-09-20 (see DECISIONS_LOG.md item 44), these
columns are now real, maintained balances, recomputed from scratch from
Childcare_ClaimMaster/Childcare_ClaimApprovalHistory every time a claim's
status changes in a way that affects them (submitted, approved, rejected,
or sent back) — rather than left at their initial zero values as before
(superseding, for these specific columns only, the "never write these"
decisions in DECISIONS_LOG.md items 20/26/32; the HR and employee
eligibility reports still compute their own figures live from claims
rather than reading these columns, and now agree with them by
construction).

Recomputing from scratch (rather than incrementally adjusting by a delta
on each transition) avoids any risk of drift from double-counting or a
missed edge case — the cost of a couple of extra aggregate queries per
transition is negligible at this application's scale.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories import eligibility_repository, report_repository


def sync_balance(db: Session, eligibility_id: int) -> None:
    approved_totals = report_repository.get_approved_totals_by_eligibility(db, [eligibility_id])
    in_progress_totals = report_repository.get_in_progress_totals_by_eligibility(
        db, [eligibility_id]
    )
    eligibility = eligibility_repository.get_by_id(db, eligibility_id)
    assert eligibility is not None

    eligibility_repository.update_balance(
        db,
        eligibility,
        approved_amount=approved_totals.get(eligibility_id, Decimal("0")),
        in_progress_amount=in_progress_totals.get(eligibility_id, Decimal("0")),
    )
