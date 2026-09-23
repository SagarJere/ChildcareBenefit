"""First-year payout (user direction 2026-09-22/23): a child's first 13
months of life are paid automatically, with no employee claim.

Increment 2 (add-child integration): a fresh child gets the right ledger
immediately, it correctly splits across two financial years when the
window spans them, and a child with nothing to auto-pay gets no ledger
rows at all (not pointless all-zero ones).

Increment 3 (claim blocking): an employee cannot raise (or edit into) a
claim whose invoice date falls within that same first-13-months window —
that period is auto-paid, not claimed.

Increment 4 (reports split): HR's Payout Report shows claim-driven
payout only; a new sibling First Year Payout Report shows the
auto-paid amounts only — same split for the employee's own view.

The calculation itself is already exhaustively unit-tested in
test_payout_calculator.py / test_eligibility_calculator.py — these tests
focus on the integration wiring.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.repositories import payout_repository


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


def _get_eligibility(client: TestClient, child_id: str, financial_year: str) -> dict:
    response = client.get(
        f"/api/v1/eligibility/{child_id}", params={"financialYear": financial_year}
    )
    rows = response.json()
    assert len(rows) == 1, rows
    return rows[0]


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def test_add_child_creates_first_year_payout_ledger_immediately(
    login_as, db_session: Session
) -> None:
    client = login_as(memp_id=910001, employee_id="91000001", Joindate=datetime(2018, 1, 1))
    # Born this month (2026-09-23) — entirely within the first-13-months
    # window for the rest of the current financial year.
    child = _add_child(client, "First Year Kid One", "2026-09-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    assert len(ledger) > 0
    for row in ledger:
        assert float(row.FirstYearPayoutAmount) == 14000.0
        assert float(row.ClaimAllocatedAmount) == 0.0
        assert float(row.CalculatedPayoutAmount) == 14000.0
    allocations = payout_repository.get_allocations_for_eligibility(db_session, eligibility_id)
    assert allocations == []


def test_add_child_splits_first_year_payout_across_two_financial_years(
    login_as, db_session: Session
) -> None:
    # Month 1 = Apr 2026, month 13 = Apr 2027, month 14 = May 2027 — so
    # the current FY (Apr 2026-Mar 2027) is entirely first-year, and the
    # next FY (Apr 2027-Mar 2028) has exactly one first-year month
    # (April) before turning claimable.
    client = login_as(memp_id=910002, employee_id="91000002", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "First Year Kid Two", "2026-04-01")

    current_fy = child["eligibility"]["financial_year"]
    current_eligibility_id = child["eligibility"]["eligibility_id"]
    current_ledger = payout_repository.get_ledger_for_eligibility(
        db_session, current_eligibility_id
    )
    assert len(current_ledger) == 12
    assert all(float(row.FirstYearPayoutAmount) == 14000.0 for row in current_ledger)
    assert all(float(row.ClaimAllocatedAmount) == 0.0 for row in current_ledger)

    next_fy = f"{int(current_fy[:4]) + 1}-{str(int(current_fy[:4]) + 2)[-2:]}"
    next_eligibility = _get_eligibility(client, child["child_id"], next_fy)
    next_ledger = payout_repository.get_ledger_for_eligibility(
        db_session, next_eligibility["eligibility_id"]
    )
    assert len(next_ledger) == 12
    first_year_rows = [row for row in next_ledger if float(row.FirstYearPayoutAmount) > 0]
    claimable_rows = [row for row in next_ledger if float(row.FirstYearPayoutAmount) == 0]
    assert len(first_year_rows) == 1
    assert float(first_year_rows[0].FirstYearPayoutAmount) == 14000.0
    assert len(claimable_rows) == 11
    assert all(float(row.ClaimAllocatedAmount) == 0.0 for row in claimable_rows)


def test_add_child_with_no_first_year_payout_creates_no_ledger_rows(
    login_as, db_session: Session
) -> None:
    # Old enough that every eligible month (current and next FY) is
    # already well past month 13 — nothing to auto-pay, so add_child
    # shouldn't create any ledger rows at all until a claim is approved.
    client = login_as(memp_id=910003, employee_id="91000003", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "First Year Kid Three", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    assert ledger == []


def test_create_claim_blocked_within_first_thirteen_months(login_as) -> None:
    client = login_as(memp_id=910005, employee_id="91000005", Joindate=datetime(2018, 1, 1))
    # Month 13 = Sep 2026 — still within the first-year-payout window.
    child = _add_child(client, "First Year Kid Five", "2025-09-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-15",
            "invoice_number": "INV-FY-1",
            "invoice_amount": "1000.00",
        },
    )
    assert response.status_code == 400
    assert "automatically" in response.json()["message"].lower()


def test_create_claim_allowed_from_month_fourteen(login_as) -> None:
    client = login_as(memp_id=910006, employee_id="91000006", Joindate=datetime(2018, 1, 1))
    # Month 13 = Jun 2026, month 14 = Jul 2026 — the first claimable
    # month, and already in the past relative to "today" (2026-09-23), so
    # a real invoice can be dated there.
    child = _add_child(client, "First Year Kid Six", "2025-06-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-07-15",
            "invoice_number": "INV-FY-2",
            "invoice_amount": "1000.00",
        },
    )
    assert response.status_code == 201, response.text


def test_update_claim_blocked_when_moved_into_first_year_period(login_as) -> None:
    client = login_as(memp_id=910007, employee_id="91000007", Joindate=datetime(2018, 1, 1))
    # Same DOB/timeline as the previous test: month 13 = Jun 2026, month
    # 14 = Jul 2026.
    child = _add_child(client, "First Year Kid Seven", "2025-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-07-15",
            "invoice_number": "INV-FY-3",
            "invoice_amount": "1000.00",
        },
    ).json()

    response = client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-06-15",
            "invoice_number": "INV-FY-3",
            "invoice_amount": "1000.00",
        },
    )
    assert response.status_code == 400
    assert "automatically" in response.json()["message"].lower()


def test_create_claim_allowed_despite_young_child_when_employee_joined_late(login_as) -> None:
    # Same shape as the add-child late-join test above: the child is
    # still within its own first-13-months window by age, but the
    # employee joined after that window closed, so eligibility (and
    # therefore claim-raising) starts at month 14 regardless.
    client = login_as(memp_id=910008, employee_id="91000008", Joindate=datetime(2026, 9, 1))
    child = _add_child(client, "First Year Kid Eight", "2025-08-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-15",
            "invoice_number": "INV-FY-4",
            "invoice_amount": "1000.00",
        },
    )
    assert response.status_code == 201, response.text


def test_add_child_with_late_joining_employee_has_no_first_year_payout(
    login_as, db_session: Session
) -> None:
    # Child born Aug 2025 (month 13 = Aug 2026) is, by age alone, still
    # within its first-year-payout window as of 2026-09-23 — but the
    # employee only joined Sep 2026, one month after that window closed,
    # so eligibility starts at month 14 and nothing is auto-paid. Confirms
    # the "employee joined late" override applies at the add-child
    # integration level too, not just in the calculator's own unit tests.
    client = login_as(memp_id=910004, employee_id="91000004", Joindate=datetime(2026, 9, 1))
    child = _add_child(client, "First Year Kid Four", "2025-08-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    assert ledger == []


def test_hr_first_year_report_shows_fresh_child_but_claim_report_does_not(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=910009, employee_id="91000009", Joindate=datetime(2018, 1, 1))
    # Born this month — entirely first-year, no claims possible at all.
    # Gets both a current- and next-FY eligibility record by default (item
    # 43), and this child is young enough that both have first-year
    # months, so two report rows are expected.
    child = _add_child(claimant, "First Year Kid Nine", "2026-09-01")

    make_employee(memp_id=910010, employee_id="91000010", Joindate=datetime(2018, 1, 1))
    make_hr_approver("91000010")
    _login_as_existing(claimant, "91000010")
    hr_client = claimant

    first_year = hr_client.get(
        "/api/v1/hr/reports/payout/first-year", params={"employee_id": "91000009"}
    )
    assert first_year.status_code == 200
    fy_rows = first_year.json()["rows"]
    assert len(fy_rows) == 2
    assert all(row["child_id"] == child["child_id"] for row in fy_rows)
    assert all(float(row["total_payout"]) > 0 for row in fy_rows)

    claim_report = hr_client.get(
        "/api/v1/hr/reports/payout", params={"employee_id": "91000009"}
    )
    assert claim_report.status_code == 200
    assert claim_report.json()["rows"] == []


def test_hr_reports_split_first_year_and_claim_payout_for_the_same_child(
    login_as, make_hr_approver, make_employee
) -> None:
    """A child whose current-FY eligibility window itself straddles the
    first-year/claimable boundary: month 13 (Apr 2026) is auto-paid,
    month 14 onward (May 2026+) is claim-driven — both already in the
    past relative to "today" (2026-09-23), so a real claim can be raised
    and approved for the claimable part."""
    claimant = login_as(memp_id=910011, employee_id="91000011", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "First Year Kid Ten", "2025-04-01")
    fy = child["eligibility"]["financial_year"]

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-FY-SPLIT",
            "invoice_amount": "9000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=910012, employee_id="91000012", Joindate=datetime(2018, 1, 1))
    make_hr_approver("91000012")
    _login_as_existing(claimant, "91000012")
    hr_client = claimant
    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    first_year = hr_client.get(
        "/api/v1/hr/reports/payout/first-year",
        params={"employee_id": "91000011", "financial_year": fy},
    )
    fy_rows = first_year.json()["rows"]
    assert len(fy_rows) == 1
    assert float(fy_rows[0]["apr"]) == 14000.0
    assert float(fy_rows[0]["may"]) == 0.0
    assert float(fy_rows[0]["total_payout"]) == 14000.0

    claim_report = hr_client.get(
        "/api/v1/hr/reports/payout", params={"employee_id": "91000011", "financial_year": fy}
    )
    claim_rows = claim_report.json()["rows"]
    assert len(claim_rows) == 1
    assert float(claim_rows[0]["apr"]) == 0.0
    assert float(claim_rows[0]["total_payout"]) == 9000.00


def test_employee_first_year_payout_report_is_scoped_to_own_children(
    login_as, make_employee
) -> None:
    claimant = login_as(memp_id=910013, employee_id="91000013", Joindate=datetime(2018, 1, 1))
    # Young enough to get both a current- and next-FY eligibility record
    # (item 43) with first-year months in both — see the previous test.
    _add_child(claimant, "First Year Kid Eleven", "2026-09-01")

    make_employee(memp_id=910014, employee_id="91000014", Joindate=datetime(2018, 1, 1))
    _login_as_existing(claimant, "91000014")
    other_view = claimant.get("/api/v1/eligibility/payout-report/first-year")
    assert other_view.status_code == 200
    assert other_view.json()["rows"] == []

    _login_as_existing(claimant, "91000013")
    own_view = claimant.get("/api/v1/eligibility/payout-report/first-year")
    assert own_view.status_code == 200
    rows = own_view.json()["rows"]
    assert len(rows) == 2
    assert all(row["employee_id"] == "91000013" for row in rows)


def test_add_child_with_first_year_payout_updates_eligibility_balance(login_as) -> None:
    """Without this, UtilizedAmount/RemainingAmount would stay at their
    initial (no-payout-yet) defaults despite real money already having
    been auto-paid for the child's first-13-months window."""
    client = login_as(memp_id=910015, employee_id="91000015", Joindate=datetime(2018, 1, 1))
    # Entire current-FY window is first-year (born this month).
    child = _add_child(client, "First Year Kid Twelve", "2026-09-01")

    eligibility = child["eligibility"]
    allotted = float(eligibility["allotted_amount"])
    expected_first_year_total = 14000.0 * eligibility["eligible_months"]
    assert allotted == expected_first_year_total

    assert float(eligibility["utilized_amount"]) == expected_first_year_total
    assert float(eligibility["approved_amount"]) == 0.0
    assert float(eligibility["remaining_amount"]) == allotted - expected_first_year_total


def test_hr_approval_cap_accounts_for_first_year_payout_already_consumed(
    login_as, make_hr_approver, make_employee
) -> None:
    """The bug this guards against: before RemainingAmount subtracted
    first-year payout too, HR could approve a claim for more than the
    payout calculator's true remaining *claimable* capacity (since
    first-year months are removed from that pool entirely — see
    payout_calculator.py) — recalculate_payout would then raise
    PayoutCapacityExceededError. Now HR's approval is correctly capped
    before that can happen."""
    claimant = login_as(memp_id=910016, employee_id="91000016", Joindate=datetime(2018, 1, 1))
    # Same DOB as the reports-split test: month 13 = Apr 2026 (first-year,
    # auto-paid 14,000), month 14 onward = May 2026+ (claimable). Current
    # FY allotment is 12 * 14000 = 168,000; true remaining claimable
    # capacity is only 11 * 14000 = 154,000.
    child = _add_child(claimant, "First Year Kid Thirteen", "2025-04-01")
    allotted = float(child["eligibility"]["allotted_amount"])
    assert allotted == 168000.0
    assert float(child["eligibility"]["remaining_amount"]) == 154000.0

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-FY-CAP",
            "invoice_amount": "160000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=910017, employee_id="91000017", Joindate=datetime(2018, 1, 1))
    make_hr_approver("91000017")
    _login_as_existing(claimant, "91000017")
    hr_client = claimant

    # 160,000 is within the (buggy) old RemainingAmount of 168,000 but
    # exceeds the true remaining claimable capacity of 154,000.
    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "160000.00"}
    )
    assert approve.status_code == 400
    assert "remaining balance" in approve.json()["message"].lower()

    # A claim within the true remaining capacity succeeds without error.
    within_capacity = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "154000.00"}
    )
    assert within_capacity.status_code == 200


def test_hr_eligibility_utilization_report_accounts_for_first_year_payout(
    login_as, make_hr_approver, make_employee
) -> None:
    """Same bug as test_hr_approval_cap_accounts_for_first_year_payout_
    already_consumed, but in the live-computed HR "Eligibility
    Utilization" report rather than the stored EligibilityMaster columns
    — build_eligibility_utilization used to compute remaining_after_
    approved from AllottedAmount minus *approved claims only*, ignoring
    first-year auto-pay entirely."""
    claimant = login_as(memp_id=910018, employee_id="91000018", Joindate=datetime(2018, 1, 1))
    # Same DOB/shape as the approval-cap test: allotted 168,000, of which
    # 14,000 is auto-paid as first-year (month 13 = Apr 2026).
    child = _add_child(claimant, "First Year Kid Fourteen", "2025-04-01")
    fy = child["eligibility"]["financial_year"]

    make_employee(memp_id=910019, employee_id="91000019", Joindate=datetime(2018, 1, 1))
    make_hr_approver("91000019")
    _login_as_existing(claimant, "91000019")
    hr_client = claimant

    report = hr_client.get(
        "/api/v1/hr/reports/eligibility-utilization",
        params={"employee_id": "91000018", "financial_year": fy},
    )
    assert report.status_code == 200
    rows = report.json()["rows"]
    assert len(rows) == 1
    assert float(rows[0]["allotted_amount"]) == 168000.0
    assert float(rows[0]["approved_amount"]) == 0.0
    assert float(rows[0]["remaining_after_approved"]) == 154000.0


def test_employee_eligibility_report_accounts_for_first_year_payout(login_as) -> None:
    """Same bug as above, in the employee-facing "Eligibility & Payout"
    report (build_employee_eligibility_report) that HomePage.tsx's
    per-FY remaining-balance breakdown consumes."""
    client = login_as(memp_id=910020, employee_id="91000020", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "First Year Kid Fifteen", "2025-04-01")
    fy = child["eligibility"]["financial_year"]

    report = client.get("/api/v1/eligibility/report")
    assert report.status_code == 200
    rows = [row for row in report.json()["rows"] if row["financial_year"] == fy]
    assert len(rows) == 1
    assert float(rows[0]["allotted_amount"]) == 168000.0
    assert float(rows[0]["utilized_amount"]) == 14000.0
    assert float(rows[0]["balance_amount"]) == 154000.0
