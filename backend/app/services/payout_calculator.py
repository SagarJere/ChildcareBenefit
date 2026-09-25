"""Pure payout calculation logic — no database access.

Implements the rules finalized in PAYOUT_REQUIREMENTS.md (confirmed by
user 2026-09-20; see DECISIONS_LOG.md items 44-48): monthly entitlement,
within-financial-year-only carry-forward, and chronological allocation
of approved claims across a child's eligible months, including
future-month allocation when a claim exceeds the entitlement accumulated
so far. "Chronological" was originally purely HR approval time; as of
user direction 2026-09-25 it's the *effective processing month* — the
later of HR's approval month and the claim's own submission-cutoff-
adjusted month — see `_effective_processing_month`. The cutoff day used
for that adjustment travels with each claim (`ApprovedClaimInput.
submission_cutoff_day`, snapshotted at submission time), not as a single
value for the whole calculation — see that field's own comment.
`calculate_payout_schedule`'s own `force_same_month_payout` (added
2026-09-25, same day) is the opposite: a single value for the whole
recompute, read live rather than snapshotted, that overrides the
cutoff-adjusted month entirely — see that parameter's own comment on
`_effective_processing_month`.

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

from app.services.eligibility_calculator import MONTHLY_BENEFIT_AMOUNT, is_first_year_payout_month


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
    # The claim's (latest, if resent back and resubmitted) submission
    # date — used only to compute the cutoff-adjusted effective month
    # below, per user direction 2026-09-25. Never used for anything else
    # (which financial year, eligibility window, etc. is still driven by
    # InvoiceDate elsewhere, unaffected).
    submitted_date: date
    # The SubmissionCutoffDay that was actually in effect when the claim
    # above was submitted — snapshotted onto the claim itself at
    # submission time (see ClaimMaster.SubmissionCutoffDayAtSubmission),
    # not the *current* org-wide setting. A full schedule rebuild (see
    # payout_service.recalculate_payout) processes many claims submitted
    # under different cutoff days if HR has changed the setting over
    # time, so this travels per-claim rather than as a single value for
    # the whole calculation — otherwise changing the cutoff day would
    # retroactively reclassify which month an already-submitted claim's
    # payout lands in (user-reported bug 2026-09-25).
    submission_cutoff_day: int


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
    first_year_payout_amount: Decimal
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


def _first_year_payout_by_month(
    first_year_months: list[date], first_year_payout_as_of_date: date
) -> dict[date, Decimal]:
    """Bundles every first-year month up through the one containing
    `first_year_payout_as_of_date` — the date this eligibility record was
    actually created — into that single month's payout, and leaves every
    later first-year month untouched at its own standalone entitlement.

    None of the months before the record existed could have been
    physically disbursed on their own, so they're rolled into the month
    the child was actually added instead of being paid (or silently
    dropped) individually — user direction 2026-09-24: child DOB Aug
    2026, added in Sep 2026, should show Sep = 14k (its own) + 14k
    (Aug's catch-up), with October onward unaffected.

    When `first_year_payout_as_of_date` falls at or before the window's
    first month (the normal case — a child added the same month it's
    born, or a next-financial-year window created well before it starts),
    the loop below never advances past index 0 and this reduces to the
    original one-month-at-a-time behavior.
    """
    if not first_year_months:
        return {}

    as_of_month = _month_start(first_year_payout_as_of_date)
    catchup_index = 0
    for index, month in enumerate(first_year_months):
        if month <= as_of_month:
            catchup_index = index
        else:
            break

    amounts: dict[date, Decimal] = {}
    for index, month in enumerate(first_year_months):
        if index < catchup_index:
            amounts[month] = Decimal("0")
        elif index == catchup_index:
            amounts[month] = MONTHLY_BENEFIT_AMOUNT * (catchup_index + 1)
        else:
            amounts[month] = MONTHLY_BENEFIT_AMOUNT
    return amounts


def _cutoff_adjusted_month(submitted_date: date, submission_cutoff_day: int) -> date:
    """The calendar month (as its first-of-month date) a claim's own
    submission makes it *eligible* for, purely from the submission date —
    the same month if submitted on or before the cutoff day of the
    month, otherwise the next month (user direction 2026-09-25: "submit
    before the 5th to get paid that month; after the 5th, next month,
    even if approved the same month")."""
    month_start = _month_start(submitted_date)
    if submitted_date.day <= submission_cutoff_day:
        return month_start
    return _add_month(month_start)


def _effective_processing_month(
    *,
    approved_at: datetime,
    submitted_date: date,
    submission_cutoff_day: int,
    force_same_month_payout: bool,
) -> date:
    """When a claim is actually processed for payout-month purposes: the
    *later* of (a) the month HR approved it (money can't move before
    it's approved) and (b) the submission's cutoff-adjusted month (a
    late submission doesn't buy back a same-month payout just because
    HR approves it quickly). This is the generalization of the two
    scenarios the user gave explicitly — submit-early+approve-same-month
    -> that month; submit-late+approve-same-month -> next month — that
    also does something sensible for the case they didn't mention
    (HR taking a long time to approve): payout follows the later,
    slower event instead of the submission's own month.

    force_same_month_payout (user direction 2026-09-25, same day as the
    financial-year gate — see Childcare_PayoutSettings.
    ForceSameMonthPayout's own comment) is an HR override for FY
    close-out: while on, the cutoff-adjusted month is ignored entirely
    and every claim pays out in its own approval month, full stop —
    deliberately still not allowed to move *before* approval, since
    that's a physical impossibility, not a policy choice."""
    if force_same_month_payout:
        return _month_start(approved_at.date())
    return max(
        _cutoff_adjusted_month(submitted_date, submission_cutoff_day),
        _month_start(approved_at.date()),
    )


def calculate_payout_schedule(
    *,
    child_dob: date,
    eligibility_start_date: date,
    eligibility_end_date: date,
    first_year_payout_as_of_date: date,
    force_same_month_payout: bool,
    approved_claims: list[ApprovedClaimInput],
) -> PayoutScheduleResult:
    """Computes the monthly payout ledger and per-claim allocation for one
    child's one financial year of eligibility.

    The child's first 13 months of life (user direction 2026-09-22) are
    paid automatically, with no claim involved and no carry-forward
    interaction with the claim-driven months that follow — see
    `_first_year_payout_by_month` for how `first_year_payout_as_of_date`
    (added 2026-09-24) bundles any first-year months missed before the
    child was actually added into the month it was added. Since child age
    only increases with calendar time, these first-year months are always
    a prefix of this eligibility window's months (never interleaved with
    claimable ones), so the claim-driven pointer/carry-forward mechanics
    below run unmodified, just scoped to the remaining "claimable" months.

    Claims are processed in chronological order of their *effective*
    processing month (PAYOUT_REQUIREMENTS.md §5, extended by user
    direction 2026-09-25 — see `_effective_processing_month`): the later
    of HR's approval month and the submission's own cutoff-adjusted
    month. Each claim first "catches up" — consuming any entitlement
    accumulated up to and including its own effective month that earlier
    claims left unconsumed, recorded as a single allocation row dated at
    that effective month — then, if its amount isn't fully covered by
    that, spills into strictly later months one at a time (§4), each such
    future month getting its own row.
    """
    months = eligible_months_between(eligibility_start_date, eligibility_end_date)
    first_year_months_set = {
        month for month in months if is_first_year_payout_month(child_dob=child_dob, month=month)
    }
    first_year_months = [month for month in months if month in first_year_months_set]
    claimable_months = [month for month in months if month not in first_year_months_set]
    first_year_payout_by_month = _first_year_payout_by_month(
        first_year_months, first_year_payout_as_of_date
    )

    # Tracks each origin month's remaining *physical* capacity, purely to
    # know how much can still be drawn from it — not what gets displayed
    # against that month in the ledger (see below).
    remaining_by_month = {month: MONTHLY_BENEFIT_AMOUNT for month in claimable_months}
    allocations: list[PayoutAllocationEntry] = []

    # The earliest month that might still have unconsumed capacity —
    # monotonically advances as months are fully consumed; never revisits
    # an earlier month once it's exhausted.
    pointer = 0

    claims_with_effective_month = [
        (
            _effective_processing_month(
                approved_at=claim.approved_at,
                submitted_date=claim.submitted_date,
                submission_cutoff_day=claim.submission_cutoff_day,
                force_same_month_payout=force_same_month_payout,
            ),
            claim,
        )
        for claim in approved_claims
    ]

    for effective_month, claim in sorted(
        claims_with_effective_month,
        key=lambda pair: (pair[0], pair[1].approved_at, pair[1].claim_id),
    ):
        remaining = claim.approved_amount
        sequence = 0
        effective_month_index = _clamp_month_index(claimable_months, effective_month)

        # Phase 1: "catch up" — bundle everything from the current
        # pointer through the claim's own effective month into one row
        # dated at that effective month.
        catchup_amount = Decimal("0")
        catchup_month = claimable_months[effective_month_index]
        while pointer <= effective_month_index and remaining > 0:
            month = claimable_months[pointer]
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
            if pointer >= len(claimable_months):
                raise PayoutCapacityExceededError(
                    f"Claim {claim.claim_id} needs {remaining} more than this "
                    "child's financial year has remaining eligible-month "
                    "capacity for — this should be unreachable if HR approval "
                    "was correctly capped at the eligibility's RemainingAmount."
                )
            month = claimable_months[pointer]
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
    allocated_by_month = {month: Decimal("0") for month in claimable_months}
    for entry in allocations:
        allocated_by_month[entry.month] += entry.allocated_amount

    ledger = []
    opening = Decimal("0")
    for month in months:
        if month in first_year_months_set:
            first_year_payout = first_year_payout_by_month[month]
            ledger.append(
                MonthlyLedgerEntry(
                    month=month,
                    entitlement_amount=MONTHLY_BENEFIT_AMOUNT,
                    opening_balance=Decimal("0"),
                    total_available_amount=first_year_payout,
                    first_year_payout_amount=first_year_payout,
                    claim_allocated_amount=Decimal("0"),
                    carry_forward_amount=Decimal("0"),
                )
            )
            continue
        available = opening + MONTHLY_BENEFIT_AMOUNT
        allocated = allocated_by_month[month]
        closing = available - allocated
        ledger.append(
            MonthlyLedgerEntry(
                month=month,
                entitlement_amount=MONTHLY_BENEFIT_AMOUNT,
                opening_balance=opening,
                total_available_amount=available,
                first_year_payout_amount=Decimal("0"),
                claim_allocated_amount=allocated,
                carry_forward_amount=closing,
            )
        )
        opening = closing

    return PayoutScheduleResult(ledger=ledger, allocations=allocations)


def _clamp_month_index(months: list[date], effective_date: date) -> int:
    """The index into `months` for the given effective-processing date's
    calendar month, clamped into range. A claim whose effective month
    falls before the eligibility window starts is treated as effective
    in the first eligible month; one falling after the window ends (e.g.
    processed just as the child ages out) is treated as effective in the
    last eligible month. Both are defensive edge cases, not expected in
    normal operation."""
    if not months:
        raise PayoutCapacityExceededError(
            "No eligible months to allocate a payout against."
        )
    approval_month = _month_start(effective_date)
    if approval_month <= months[0]:
        return 0
    if approval_month >= months[-1]:
        return len(months) - 1
    return months.index(approval_month)
