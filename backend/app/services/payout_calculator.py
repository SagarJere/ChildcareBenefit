"""Pure payout calculation logic — no database access.

Implements the rules finalized in PAYOUT_REQUIREMENTS.md (confirmed by
user 2026-09-20; see DECISIONS_LOG.md items 44-48): monthly entitlement,
within-financial-year-only carry-forward, and chronological (by HR
approval time) allocation of approved claims across a child's eligible
months, including future-month allocation when a claim exceeds the
entitlement accumulated so far.

Kept dependency-free and side-effect-free, mirroring
eligibility_calculator.py, so every scenario in PAYOUT_REQUIREMENTS.md
can be tested directly without a database. Scoped to exactly one
(child, financial year) at a time — carry-forward never crosses a
financial year boundary (PAYOUT_REQUIREMENTS.md §3), so this module has
no way to reach across one.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.services.eligibility_calculator import MONTHLY_BENEFIT_AMOUNT


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def eligible_months_between(start_date: date, end_date: date) -> list[date]:
    """The ordered list of calendar months (as their first-of-month date)
    from `start_date` through `end_date`, inclusive. Both are expected to
    already be month-aligned in practice (EligibilityMaster.
    EligibilityStartDate is always a month start; EligibilityEndDate is
    always a month end), but this normalizes defensively either way."""
    months = []
    current = _month_start(start_date)
    last = _month_start(end_date)
    while current <= last:
        months.append(current)
        current = _add_month(current)
    return months


@dataclass(frozen=True)
class ApprovedClaimInput:
    claim_id: int
    approved_amount: Decimal
    approved_at: datetime


@dataclass(frozen=True)
class PayoutAllocationEntry:
    claim_id: int
    month: date
    allocated_amount: Decimal
    allocation_sequence: int


@dataclass(frozen=True)
class MonthlyLedgerEntry:
    month: date
    entitlement_amount: Decimal
    opening_balance: Decimal
    total_available_amount: Decimal
    claim_allocated_amount: Decimal
    carry_forward_amount: Decimal


@dataclass(frozen=True)
class PayoutScheduleResult:
    ledger: list[MonthlyLedgerEntry] = field(default_factory=list)
    allocations: list[PayoutAllocationEntry] = field(default_factory=list)


class PayoutCapacityExceededError(Exception):
    """The approved claims for this (child, financial year) together
    exceed the total entitlement across its eligible months.

    This should be mathematically unreachable as long as HR approval is
    correctly capped at the eligibility's own RemainingAmount (see
    DECISIONS_LOG.md items 44-45) — raised instead of silently dropping
    money if that invariant is ever violated.
    """


def calculate_payout_schedule(
    *,
    eligibility_start_date: date,
    eligibility_end_date: date,
    approved_claims: list[ApprovedClaimInput],
) -> PayoutScheduleResult:
    """Computes the monthly payout ledger and per-claim allocation for one
    child's one financial year of eligibility.

    Claims are processed in chronological order of `approved_at`
    (PAYOUT_REQUIREMENTS.md §5). Each claim first "catches up" — consuming
    any entitlement accumulated up to and including its own approval
    month that earlier claims left unconsumed, recorded as a single
    allocation row dated at the claim's own approval month — then, if its
    amount isn't fully covered by that, spills into strictly later months
    one at a time (§4), each such future month getting its own row.
    """
    months = eligible_months_between(eligibility_start_date, eligibility_end_date)
    # Tracks each origin month's remaining *physical* capacity, purely to
    # know how much can still be drawn from it — not what gets displayed
    # against that month in the ledger (see below).
    remaining_by_month = {month: MONTHLY_BENEFIT_AMOUNT for month in months}
    allocations: list[PayoutAllocationEntry] = []

    # The earliest month that might still have unconsumed capacity —
    # monotonically advances as months are fully consumed; never revisits
    # an earlier month once it's exhausted.
    pointer = 0

    for claim in sorted(approved_claims, key=lambda c: (c.approved_at, c.claim_id)):
        remaining = claim.approved_amount
        sequence = 0
        approval_month_index = _clamp_month_index(months, claim.approved_at.date())

        # Phase 1: "catch up" — bundle everything from the current
        # pointer through the claim's own approval month into one row
        # dated at the approval month.
        catchup_amount = Decimal("0")
        catchup_month = months[approval_month_index]
        while pointer <= approval_month_index and remaining > 0:
            month = months[pointer]
            take = min(remaining_by_month[month], remaining)
            remaining_by_month[month] -= take
            remaining -= take
            catchup_amount += take
            if remaining_by_month[month] == 0:
                pointer += 1
            else:
                break
        if catchup_amount > 0:
            sequence += 1
            allocations.append(
                PayoutAllocationEntry(
                    claim_id=claim.claim_id,
                    month=catchup_month,
                    allocated_amount=catchup_amount,
                    allocation_sequence=sequence,
                )
            )

        # Phase 2: spill into strictly future months, one row each.
        while remaining > 0:
            if pointer >= len(months):
                raise PayoutCapacityExceededError(
                    f"Claim {claim.claim_id} needs {remaining} more than this "
                    "child's financial year has remaining eligible-month "
                    "capacity for — this should be unreachable if HR approval "
                    "was correctly capped at the eligibility's RemainingAmount."
                )
            month = months[pointer]
            take = min(remaining_by_month[month], remaining)
            remaining_by_month[month] -= take
            remaining -= take
            if take > 0:
                sequence += 1
                allocations.append(
                    PayoutAllocationEntry(
                        claim_id=claim.claim_id,
                        month=month,
                        allocated_amount=take,
                        allocation_sequence=sequence,
                    )
                )
            if remaining_by_month[month] == 0:
                pointer += 1
            else:
                break

    # The ledger's per-month "allocated" figure is what actually got
    # *billed* to that month (the allocation rows' attributed month, after
    # catch-up bundling) — not which origin month's raw capacity was
    # physically drawn from. This is why September shows only its own
    # claim's 9,000 even if a later claim's catch-up also reached back
    # into September's unconsumed 5,000 — that reach-back is billed to
    # the later claim's own approval month instead (PAYOUT_REQUIREMENTS.md
    # §4-5's worked examples).
    allocated_by_month = {month: Decimal("0") for month in months}
    for entry in allocations:
        allocated_by_month[entry.month] += entry.allocated_amount

    ledger = []
    opening = Decimal("0")
    for month in months:
        available = opening + MONTHLY_BENEFIT_AMOUNT
        allocated = allocated_by_month[month]
        closing = available - allocated
        ledger.append(
            MonthlyLedgerEntry(
                month=month,
                entitlement_amount=MONTHLY_BENEFIT_AMOUNT,
                opening_balance=opening,
                total_available_amount=available,
                claim_allocated_amount=allocated,
                carry_forward_amount=closing,
            )
        )
        opening = closing

    return PayoutScheduleResult(ledger=ledger, allocations=allocations)


def _clamp_month_index(months: list[date], approval_date: date) -> int:
    """The index into `months` for the given approval date's calendar
    month, clamped into range. A claim approved before the eligibility
    window starts is treated as approved in the first eligible month; one
    approved after the window ends (e.g. processed just as the child ages
    out) is treated as approved in the last eligible month. Both are
    defensive edge cases, not expected in normal operation."""
    if not months:
        raise PayoutCapacityExceededError(
            "No eligible months to allocate a payout against."
        )
    approval_month = _month_start(approval_date)
    if approval_month <= months[0]:
        return 0
    if approval_month >= months[-1]:
        return len(months) - 1
    return months.index(approval_month)
