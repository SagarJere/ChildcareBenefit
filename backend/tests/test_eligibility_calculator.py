from datetime import date

from app.services.eligibility_calculator import (
    calculate_eligibility,
    child_month_number,
    claim_requires_documents,
    compute_financial_year,
    next_financial_year_needed,
    next_financial_year_window,
)


class TestComputeFinancialYear:
    def test_april_first_starts_new_financial_year(self) -> None:
        fy = compute_financial_year(date(2026, 4, 1))
        assert fy.label == "2026-27"
        assert fy.start_date == date(2026, 4, 1)
        assert fy.end_date == date(2027, 3, 31)

    def test_march_thirty_first_is_still_previous_financial_year(self) -> None:
        fy = compute_financial_year(date(2026, 3, 31))
        assert fy.label == "2025-26"
        assert fy.start_date == date(2025, 4, 1)
        assert fy.end_date == date(2026, 3, 31)

    def test_mid_year_date(self) -> None:
        fy = compute_financial_year(date(2026, 11, 15))
        assert fy.label == "2026-27"


class TestEligibilityStartMonth:
    def test_starts_at_fy_start_when_employee_and_child_predate_fy(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 10),
            child_dob=date(2022, 5, 20),
            as_of=date(2026, 6, 1),
        )
        assert result.financial_year == "2026-27"
        assert result.eligibility_start_date == date(2026, 4, 1)

    def test_starts_at_join_month_when_employee_joins_mid_fy(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2026, 7, 20),
            child_dob=date(2022, 5, 20),
            as_of=date(2026, 9, 1),
        )
        assert result.eligibility_start_date == date(2026, 7, 1)

    def test_starts_at_child_dob_month_when_child_born_mid_fy(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 10),
            child_dob=date(2026, 8, 3),
            as_of=date(2026, 9, 1),
        )
        assert result.eligibility_start_date == date(2026, 8, 1)

    def test_start_is_latest_of_all_three_candidates(self) -> None:
        # Employee joins in June (current FY), child born in August (later) —
        # August should win.
        result = calculate_eligibility(
            employee_join_date=date(2026, 6, 1),
            child_dob=date(2026, 8, 15),
            as_of=date(2026, 9, 1),
        )
        assert result.eligibility_start_date == date(2026, 8, 1)


class TestSixYearLimit:
    def test_full_financial_year_when_child_well_under_six(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 1),
            child_dob=date(2023, 6, 1),
            as_of=date(2026, 6, 1),
        )
        assert result.eligibility_start_date == date(2026, 4, 1)
        assert result.eligibility_end_date == date(2027, 3, 31)
        assert result.eligible_months == 12

    def test_eligibility_ends_in_the_birthday_month_inclusive(self) -> None:
        # DOB 2020-06-15 -> turns 6 on 2026-06-15 -> last eligible month is
        # June 2026 in full (confirmed business decision).
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 1),
            child_dob=date(2020, 6, 15),
            as_of=date(2026, 4, 1),
        )
        assert result.eligibility_start_date == date(2026, 4, 1)
        assert result.eligibility_end_date == date(2026, 6, 30)
        assert result.eligible_months == 3  # April, May, June

    def test_zero_months_when_child_already_past_six_before_start_month(self) -> None:
        # Employee joins in 2026-08 (this FY); child already turned 6 in
        # 2026-03 — by the time the employee could start claiming, the
        # child had already aged out.
        result = calculate_eligibility(
            employee_join_date=date(2026, 8, 1),
            child_dob=date(2020, 3, 10),
            as_of=date(2026, 9, 1),
        )
        assert result.eligible_months == 0
        assert result.eligibility_end_date is None
        assert result.allotted_amount == 0

    def test_leap_day_dob_clamps_to_feb_28_on_non_leap_sixth_year(self) -> None:
        # 2020 is a leap year (Feb 29 exists); 2026 is not.
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 1),
            child_dob=date(2020, 2, 29),
            as_of=date(2026, 1, 1),
        )
        assert result.eligibility_end_date == date(2026, 2, 28)


class TestMonetaryCalculation:
    def test_monthly_benefit_amount_is_always_14000(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 1),
            child_dob=date(2023, 6, 1),
            as_of=date(2026, 6, 1),
        )
        assert result.monthly_benefit_amount == 14_000

    def test_allotted_amount_is_months_times_monthly_rate(self) -> None:
        result = calculate_eligibility(
            employee_join_date=date(2018, 1, 1),
            child_dob=date(2023, 6, 1),
            as_of=date(2026, 6, 1),
        )
        assert result.allotted_amount == result.eligible_months * 14_000
        assert result.allotted_amount == 168_000


class TestNextFinancialYearWindow:
    def test_returns_the_immediately_following_financial_year(self) -> None:
        current_fy = compute_financial_year(date(2026, 6, 1))  # 2026-27
        next_fy = next_financial_year_window(current_fy)
        assert next_fy.label == "2027-28"
        assert next_fy.start_date == date(2027, 4, 1)
        assert next_fy.end_date == date(2028, 3, 31)


class TestNextFinancialYearNeeded:
    def test_needed_when_child_well_under_six(self) -> None:
        current_fy = compute_financial_year(date(2026, 6, 1))  # 2026-27
        assert next_financial_year_needed(child_dob=date(2023, 6, 1), current_fy=current_fy)

    def test_not_needed_when_six_year_cutoff_falls_within_current_fy(self) -> None:
        # DOB 2020-06-15 -> turns 6 on 2026-06-15 -> cutoff month is June
        # 2026, which is within FY 2026-27 -> nothing left to allot in
        # FY 2027-28.
        current_fy = compute_financial_year(date(2026, 4, 1))  # 2026-27
        assert not next_financial_year_needed(child_dob=date(2020, 6, 15), current_fy=current_fy)

    def test_not_needed_when_child_already_past_six(self) -> None:
        current_fy = compute_financial_year(date(2026, 4, 1))  # 2026-27
        assert not next_financial_year_needed(child_dob=date(2019, 1, 1), current_fy=current_fy)

    def test_needed_when_six_year_cutoff_falls_exactly_at_start_of_next_fy(self) -> None:
        # DOB 2021-04-15 -> turns 6 on 2027-04-15 -> cutoff month is
        # April 2027, the first month of FY 2027-28 -> that FY still has
        # one eligible month.
        current_fy = compute_financial_year(date(2026, 4, 1))  # 2026-27
        assert next_financial_year_needed(child_dob=date(2021, 4, 15), current_fy=current_fy)


class TestChildMonthNumber:
    def test_birth_month_is_month_one(self) -> None:
        assert child_month_number(child_dob=date(2023, 6, 15), invoice_date=date(2023, 6, 30)) == 1

    def test_month_counts_from_dob_regardless_of_day(self) -> None:
        # DOB on the 15th; an invoice dated the 1st of the 13th month is
        # still month 13 (whole-month granularity, like eligibility).
        assert child_month_number(child_dob=date(2023, 6, 15), invoice_date=date(2024, 6, 1)) == 13

    def test_month_twelve_is_the_last_document_free_month(self) -> None:
        assert child_month_number(child_dob=date(2023, 6, 1), invoice_date=date(2024, 5, 1)) == 12


class TestClaimRequiresDocuments:
    def test_months_one_through_twelve_do_not_require_documents(self) -> None:
        # Boundary checks: the first month and the last document-free month.
        assert not claim_requires_documents(
            child_dob=date(2023, 6, 1), invoice_date=date(2023, 6, 1)
        )
        assert not claim_requires_documents(
            child_dob=date(2023, 6, 1), invoice_date=date(2024, 5, 1)
        )

    def test_month_thirteen_onward_requires_documents(self) -> None:
        assert claim_requires_documents(child_dob=date(2023, 6, 1), invoice_date=date(2024, 6, 1))
        assert claim_requires_documents(child_dob=date(2023, 6, 1), invoice_date=date(2026, 1, 1))

    def test_child_enrolled_late_is_already_past_month_twelve(self) -> None:
        # Confirmed business decision: month is counted from DOB, not from
        # when the employee joined or eligibility began.
        assert claim_requires_documents(child_dob=date(2020, 1, 1), invoice_date=date(2026, 9, 1))
