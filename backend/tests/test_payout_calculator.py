from datetime import date, datetime
from decimal import Decimal

import pytest

from app.services.payout_calculator import (
    ApprovedClaimInput,
    PayoutCapacityExceededError,
    calculate_payout_schedule,
    eligible_months_between,
)


class TestEligibleMonthsBetween:
    def test_single_month(self) -> None:
        assert eligible_months_between(date(2026, 9, 1), date(2026, 9, 30)) == [date(2026, 9, 1)]

    def test_spans_year_boundary(self) -> None:
        months = eligible_months_between(date(2026, 12, 1), date(2027, 2, 28))
        assert months == [date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1)]


class TestNoClaims:
    def test_entitlement_accrues_and_fully_carries_forward(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 4, 1),
            first_year_payout_as_of_date=date(2026, 4, 1),
            eligibility_end_date=date(2026, 6, 30),
            approved_claims=[],
        )
        assert result.allocations == []
        assert [entry.claim_allocated_amount for entry in result.ledger] == [0, 0, 0]
        assert [entry.carry_forward_amount for entry in result.ledger] == [
            14000,
            28000,
            42000,
        ]


class TestSingleClaimWithinOneMonth:
    def test_claim_smaller_than_first_month_entitlement(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("9000"), approved_at=datetime(2026, 9, 15)
                )
            ],
        )
        assert result.allocations == [
            _alloc(1, date(2026, 9, 1), 9000, 1),
        ]
        sep = result.ledger[0]
        assert sep.claim_allocated_amount == 9000
        assert sep.carry_forward_amount == 5000


class TestFutureMonthAllocation:
    """A single claim, with no prior claims competing for capacity,
    approved for far more than its own month's accumulated entitlement —
    it spills into as many future months as it needs."""

    def test_single_claim_with_no_prior_competition_spills_forward(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("50000"), approved_at=datetime(2026, 11, 20)
                )
            ],
        )
        # No earlier claim exists, so the claim's catch-up bundles the
        # *entire* Sep+Oct+Nov entitlement (42,000) into its November row,
        # then spills 8,000 more into December.
        assert result.allocations == [
            _alloc(1, date(2026, 11, 1), 42000, 1),
            _alloc(1, date(2026, 12, 1), 8000, 2),
        ]
        by_month = {entry.month: entry for entry in result.ledger}
        assert by_month[date(2026, 9, 1)].claim_allocated_amount == 0
        assert by_month[date(2026, 9, 1)].carry_forward_amount == 14000
        assert by_month[date(2026, 10, 1)].claim_allocated_amount == 0
        assert by_month[date(2026, 10, 1)].carry_forward_amount == 28000
        assert by_month[date(2026, 11, 1)].claim_allocated_amount == 42000
        assert by_month[date(2026, 11, 1)].carry_forward_amount == 0
        assert by_month[date(2026, 12, 1)].claim_allocated_amount == 8000
        assert by_month[date(2026, 12, 1)].carry_forward_amount == 6000


class TestFullBusinessExampleFromSpec:
    """PAYOUT_REQUIREMENTS.md §18's complete flow: three claims against
    one child's eligibility, verified against every figure in the spec's
    own tables."""

    def _schedule(self):
        return calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("9000"), approved_at=datetime(2026, 9, 10)
                ),
                ApprovedClaimInput(
                    claim_id=2, approved_amount=Decimal("50000"), approved_at=datetime(2026, 11, 20)
                ),
                ApprovedClaimInput(
                    claim_id=3, approved_amount=Decimal("15000"), approved_at=datetime(2027, 1, 10)
                ),
            ],
        )

    def test_claim_allocations_match_the_spec_exactly(self) -> None:
        result = self._schedule()
        assert result.allocations == [
            _alloc(1, date(2026, 9, 1), 9000, 1),
            _alloc(2, date(2026, 11, 1), 33000, 1),
            _alloc(2, date(2026, 12, 1), 14000, 2),
            _alloc(2, date(2027, 1, 1), 3000, 3),
            _alloc(3, date(2027, 1, 1), 11000, 1),
            _alloc(3, date(2027, 2, 1), 4000, 2),
        ]

    def test_monthly_ledger_matches_the_spec_exactly(self) -> None:
        result = self._schedule()
        by_month = {entry.month: entry for entry in result.ledger}

        assert by_month[date(2026, 9, 1)].claim_allocated_amount == 9000
        assert by_month[date(2026, 9, 1)].carry_forward_amount == 5000

        assert by_month[date(2026, 10, 1)].claim_allocated_amount == 0
        assert by_month[date(2026, 10, 1)].carry_forward_amount == 19000

        assert by_month[date(2026, 11, 1)].claim_allocated_amount == 33000
        assert by_month[date(2026, 11, 1)].carry_forward_amount == 0

        assert by_month[date(2026, 12, 1)].claim_allocated_amount == 14000
        assert by_month[date(2026, 12, 1)].carry_forward_amount == 0

        assert by_month[date(2027, 1, 1)].claim_allocated_amount == 14000  # 3000 + 11000
        assert by_month[date(2027, 1, 1)].carry_forward_amount == 0

        assert by_month[date(2027, 2, 1)].claim_allocated_amount == 4000
        assert by_month[date(2027, 2, 1)].carry_forward_amount == 10000

        assert by_month[date(2027, 3, 1)].claim_allocated_amount == 0
        assert by_month[date(2027, 3, 1)].carry_forward_amount == 24000  # 10000 + 14000

    def test_original_claim_amounts_are_recoverable_from_allocations(self) -> None:
        """Section 5's invariant: a claim's total allocation must always
        sum back to its own approved amount, regardless of how many
        months it's split across."""
        result = self._schedule()
        totals: dict[int, Decimal] = {}
        for entry in result.allocations:
            totals[entry.claim_id] = (
                totals.get(entry.claim_id, Decimal("0")) + entry.allocated_amount
            )
        assert totals == {1: 9000, 2: 50000, 3: 15000}


class TestChronologicalOrderingIsByApprovalTimeNotInputOrder:
    def test_claims_are_sorted_internally(self) -> None:
        out_of_order = [
            ApprovedClaimInput(
                claim_id=2, approved_amount=Decimal("50000"), approved_at=datetime(2026, 11, 20)
            ),
            ApprovedClaimInput(
                claim_id=1, approved_amount=Decimal("9000"), approved_at=datetime(2026, 9, 10)
            ),
        ]
        in_order = list(reversed(out_of_order))

        result_a = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=out_of_order,
        )
        result_b = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=in_order,
        )
        assert result_a.allocations == result_b.allocations
        assert result_a.ledger == result_b.ledger


class TestEligibilityBoundary:
    def test_claim_exactly_exhausts_all_remaining_capacity(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2027, 1, 1),
            first_year_payout_as_of_date=date(2027, 1, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("42000"), approved_at=datetime(2027, 1, 5)
                )
            ],
        )
        assert result.allocations == [
            _alloc(1, date(2027, 1, 1), 14000, 1),
            _alloc(1, date(2027, 2, 1), 14000, 2),
            _alloc(1, date(2027, 3, 1), 14000, 3),
        ]
        assert all(entry.carry_forward_amount == 0 for entry in result.ledger)

    def test_claim_exceeding_total_capacity_raises(self) -> None:
        """Should be unreachable given HR approval's own cap
        (DECISIONS_LOG.md item 44) — raised loudly rather than silently
        dropping money if that invariant is ever violated."""
        with pytest.raises(PayoutCapacityExceededError):
            calculate_payout_schedule(
                child_dob=date(2015, 1, 1),
                eligibility_start_date=date(2027, 1, 1),
                first_year_payout_as_of_date=date(2027, 1, 1),
                eligibility_end_date=date(2027, 3, 31),
                approved_claims=[
                    ApprovedClaimInput(
                        claim_id=1,
                        approved_amount=Decimal("42000.01"),
                        approved_at=datetime(2027, 1, 5),
                    )
                ],
            )

    def test_single_eligible_month_child_close_to_six_year_cutoff(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 6, 1),
            first_year_payout_as_of_date=date(2026, 6, 1),
            eligibility_end_date=date(2026, 6, 30),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("14000"), approved_at=datetime(2026, 6, 10)
                )
            ],
        )
        assert result.allocations == [_alloc(1, date(2026, 6, 1), 14000, 1)]
        assert len(result.ledger) == 1


class TestFirstYearPayout:
    """User direction 2026-09-22: a child's first 13 months of life are
    paid automatically, with no claim involved."""

    def test_entire_window_within_first_thirteen_months_is_fully_auto_paid(self) -> None:
        # child_dob's month is month 1; the window runs exactly through
        # month 13 (Jan 2026 - Jan 2027).
        result = calculate_payout_schedule(
            child_dob=date(2026, 1, 1),
            eligibility_start_date=date(2026, 1, 1),
            first_year_payout_as_of_date=date(2026, 1, 1),
            eligibility_end_date=date(2027, 1, 31),
            approved_claims=[],
        )
        assert result.allocations == []
        assert len(result.ledger) == 13
        for entry in result.ledger:
            assert entry.first_year_payout_amount == 14000
            assert entry.claim_allocated_amount == 0
            assert entry.opening_balance == 0
            assert entry.total_available_amount == 14000
            assert entry.carry_forward_amount == 0

    def test_window_spanning_the_first_year_boundary_splits_cleanly(self) -> None:
        # child_dob's month is month 1 = Jul 2025, so month 13 = Jul 2026
        # and month 14 = Aug 2026. Window: May 2026 (month 11) through
        # Oct 2026 (month 16) — 3 first-year months, 3 claimable months.
        result = calculate_payout_schedule(
            child_dob=date(2025, 7, 1),
            eligibility_start_date=date(2026, 5, 1),
            first_year_payout_as_of_date=date(2026, 5, 1),
            eligibility_end_date=date(2026, 10, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("9000"), approved_at=datetime(2026, 8, 15)
                )
            ],
        )
        by_month = {entry.month: entry for entry in result.ledger}

        for month in (date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1)):
            assert by_month[month].first_year_payout_amount == 14000
            assert by_month[month].claim_allocated_amount == 0
            assert by_month[month].opening_balance == 0
            assert by_month[month].carry_forward_amount == 0

        # The first claimable month (Aug) starts fresh at opening=0 —
        # nothing carries over from the first-year months.
        august = by_month[date(2026, 8, 1)]
        assert august.first_year_payout_amount == 0
        assert august.opening_balance == 0
        assert august.claim_allocated_amount == 9000
        assert august.carry_forward_amount == 5000

        assert result.allocations == [_alloc(1, date(2026, 8, 1), 9000, 1)]

    def test_child_already_past_month_thirteen_has_no_first_year_months(self) -> None:
        # Mirrors the "employee joined late" case: by the time eligibility
        # begins the child is already well past month 13, so nothing is
        # auto-paid — this falls out of the month check naturally, no
        # special case needed.
        result = calculate_payout_schedule(
            child_dob=date(2015, 1, 1),
            eligibility_start_date=date(2026, 9, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[],
        )
        assert all(entry.first_year_payout_amount == 0 for entry in result.ledger)


class TestFirstYearPayoutCatchUp:
    """User direction 2026-09-24: a child born in one month but only added
    to the system in a later month should have every first-year month
    missed in between bundled into the month it was actually added —
    "if Child DOB in Aug 26 and we added the details in Sep 26 then Sep
    26 should have 14k + 14k and rest remains as it is"."""

    def test_child_added_one_month_after_birth_bundles_into_added_month(self) -> None:
        result = calculate_payout_schedule(
            child_dob=date(2026, 8, 1),
            eligibility_start_date=date(2026, 8, 1),
            first_year_payout_as_of_date=date(2026, 9, 15),
            eligibility_end_date=date(2027, 3, 31),
            approved_claims=[],
        )
        by_month = {entry.month: entry for entry in result.ledger}

        assert by_month[date(2026, 8, 1)].first_year_payout_amount == 0
        assert by_month[date(2026, 9, 1)].first_year_payout_amount == 28000
        for month in (date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1)):
            assert by_month[month].first_year_payout_amount == 14000
        assert by_month[date(2027, 1, 1)].first_year_payout_amount == 14000
        assert by_month[date(2027, 2, 1)].first_year_payout_amount == 14000
        assert by_month[date(2027, 3, 1)].first_year_payout_amount == 14000

    def test_child_added_several_months_after_birth_bundles_every_missed_month(self) -> None:
        # Month 1 = Jan 2026, added in Sep 2026 (month 9) — Jan through
        # Sep (9 months) are all bundled into September's own row.
        result = calculate_payout_schedule(
            child_dob=date(2026, 1, 1),
            eligibility_start_date=date(2026, 1, 1),
            first_year_payout_as_of_date=date(2026, 9, 1),
            eligibility_end_date=date(2027, 1, 31),
            approved_claims=[],
        )
        by_month = {entry.month: entry for entry in result.ledger}

        for month in (
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
            date(2026, 7, 1),
            date(2026, 8, 1),
        ):
            assert by_month[month].first_year_payout_amount == 0
        assert by_month[date(2026, 9, 1)].first_year_payout_amount == 126000  # 9 * 14000
        # Month 13 (Jan 2027) is the last first-year month — still its own
        # standalone entitlement, untouched by the earlier catch-up.
        assert by_month[date(2027, 1, 1)].first_year_payout_amount == 14000

        total_first_year_payout = sum(
            entry.first_year_payout_amount for entry in result.ledger
        )
        assert total_first_year_payout == 13 * 14000

    def test_child_added_before_window_starts_has_no_catchup(self) -> None:
        # Mirrors the next-financial-year eligibility record, created at
        # the same time as the current-FY one but well before its own
        # window starts — nothing was ever missed, so no bundling.
        result = calculate_payout_schedule(
            child_dob=date(2026, 8, 1),
            eligibility_start_date=date(2027, 4, 1),
            first_year_payout_as_of_date=date(2026, 9, 15),
            eligibility_end_date=date(2027, 8, 31),
            approved_claims=[],
        )
        assert all(entry.first_year_payout_amount == 14000 for entry in result.ledger)

    def test_catchup_does_not_affect_claim_driven_months_that_follow(self) -> None:
        # Same shape as test_window_spanning_the_first_year_boundary_
        # splits_cleanly, but the child is added a month late (Jun 2026
        # instead of May) — only the first-year months are bundled; the
        # claimable months' carry-forward mechanics are untouched.
        result = calculate_payout_schedule(
            child_dob=date(2025, 7, 1),
            eligibility_start_date=date(2026, 5, 1),
            first_year_payout_as_of_date=date(2026, 6, 1),
            eligibility_end_date=date(2026, 10, 31),
            approved_claims=[
                ApprovedClaimInput(
                    claim_id=1, approved_amount=Decimal("9000"), approved_at=datetime(2026, 8, 15)
                )
            ],
        )
        by_month = {entry.month: entry for entry in result.ledger}

        assert by_month[date(2026, 5, 1)].first_year_payout_amount == 0
        assert by_month[date(2026, 6, 1)].first_year_payout_amount == 28000
        assert by_month[date(2026, 7, 1)].first_year_payout_amount == 14000

        august = by_month[date(2026, 8, 1)]
        assert august.first_year_payout_amount == 0
        assert august.opening_balance == 0
        assert august.claim_allocated_amount == 9000
        assert august.carry_forward_amount == 5000
        assert result.allocations == [_alloc(1, date(2026, 8, 1), 9000, 1)]


def _alloc(claim_id: int, month: date, amount: int, sequence: int):
    from app.services.payout_calculator import PayoutAllocationEntry

    return PayoutAllocationEntry(
        claim_id=claim_id,
        month=month,
        allocated_amount=Decimal(amount),
        allocation_sequence=sequence,
    )
