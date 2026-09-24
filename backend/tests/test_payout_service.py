"""Payout persistence tests — Increment 2 (PAYOUT_REQUIREMENTS.md).

Verifies that approving a claim actually persists the correct
Childcare_PayoutMonthlyLedger / Childcare_PayoutAllocation rows via
app/services/payout_service.recalculate_payout, wired into
hr_service.approve_claim. The calculation logic itself is already
exhaustively unit-tested in test_payout_calculator.py — these tests
focus on the database wiring: full-rebuild across multiple approvals,
and that rejecting/sending back a claim does not create payout rows.

Payout allocation is anchored to the HR *approval* timestamp, not the
claim's invoice date (PAYOUT_REQUIREMENTS.md §5) — so to exercise
cross-month spillover deterministically, the multi-claim test below
directly backdates Childcare_ClaimApprovalHistory.ActionDate (the same
"insert synthetic precondition rows directly" pattern test_claims.py
already uses for attachments) and re-triggers the recompute, since three
real approvals made seconds apart in a test run would otherwise all land
in the same real calendar month.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.claim_approval_history import APPROVED as HISTORY_APPROVED
from app.models.claim_approval_history import ClaimApprovalHistory
from app.repositories import payout_repository
from app.services import payout_service


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def _create_and_submit_claim(
    client: TestClient, child_id: str, *, invoice_date: str, invoice_number: str, amount: str
) -> dict:
    created = client.post(
        "/api/v1/claims",
        json={
            "child_id": child_id,
            "invoice_date": invoice_date,
            "invoice_number": invoice_number,
            "invoice_amount": amount,
            "institution_name": "Test Institution",
            "from_date": invoice_date,
            "to_date": invoice_date,
        },
    )
    assert created.status_code == 201, created.text
    claim = created.json()
    submitted = client.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert submitted.status_code == 200, submitted.text
    return claim


def test_approving_a_single_claim_persists_ledger_and_allocation(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    claimant = login_as(memp_id=970001, employee_id="97000001", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23), so this claim-approval test isn't affected by
    # that unrelated feature.
    child = _add_child(claimant, "Payout Kid One", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]
    claim = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-01",
        invoice_number="INV-PO-1",
        amount="9000.00",
    )

    make_employee(memp_id=970002, employee_id="97000002", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000002")
    _login_as_existing(claimant, "97000002")
    hr_client = claimant

    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    allocations = payout_repository.get_allocations_for_eligibility(db_session, eligibility_id)

    # The claim is approved "now" (real time), so its catch-up lands in
    # whichever month that is — not necessarily the invoice's own month
    # (PAYOUT_REQUIREMENTS.md §5: allocation follows approval time).
    assert len(allocations) == 1
    assert allocations[0].ClaimID == claim["claim_id"]
    assert float(allocations[0].AllocatedAmount) == 9000.00
    assert allocations[0].AllocationSequence == 1

    total_allocated = sum(float(row.ClaimAllocatedAmount) for row in ledger)
    assert total_allocated == 9000.00
    anchor_row = next(row for row in ledger if row.PayoutMonth == allocations[0].PayoutMonth)
    assert float(anchor_row.ClosingBalance) == float(anchor_row.TotalAvailableAmount) - 9000.00


def test_full_worked_example_persists_correctly_across_multiple_approvals(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    """Reproduces PAYOUT_REQUIREMENTS.md §18's full flow end-to-end
    through the real API and real database: three claims, approved in
    order, against a child eligible for the whole financial year.

    Approval timestamps are backdated to Sep/Nov/Jan (see module
    docstring) so the ledger/allocation can be checked against the exact
    figures in the spec's own worked example, deterministically."""
    # Joined in September so eligibility *starts* in September, matching
    # PAYOUT_REQUIREMENTS.md §18's "eligibility begins in September" —
    # not just "the first claim happens to be approved in September" with
    # months of pre-accumulated carry-forward already sitting there. Driven
    # by the employee's join date rather than the child's DOB, and the
    # child is old enough to be well past the first-13-months
    # first-year-payout window (2026-09-23) — this test is specifically
    # about claim-driven payout, unrelated to that feature.
    claimant = login_as(memp_id=970003, employee_id="97000003", Joindate=datetime(2026, 9, 1))
    child = _add_child(claimant, "Payout Kid Two", "2024-09-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    claim_a = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-01",
        invoice_number="INV-PO-A",
        amount="9000.00",
    )
    claim_b = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-02",
        invoice_number="INV-PO-B",
        amount="50000.00",
    )
    claim_c = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-03",
        invoice_number="INV-PO-C",
        amount="15000.00",
    )

    make_employee(memp_id=970004, employee_id="97000004", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000004")
    _login_as_existing(claimant, "97000004")
    hr_client = claimant

    for claim, amount in ((claim_a, "9000.00"), (claim_b, "50000.00"), (claim_c, "15000.00")):
        response = hr_client.post(
            f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": amount}
        )
        assert response.status_code == 200, response.text

    # Backdate each claim's Approved history entry to the spec's own
    # worked-example timeline, then re-run the recompute so the ledger
    # reflects that timeline instead of the real (near-identical) approval
    # timestamps from the loop above.
    backdated_approval_times = {
        claim_a["claim_id"]: datetime(2026, 9, 10),
        claim_b["claim_id"]: datetime(2026, 11, 20),
        claim_c["claim_id"]: datetime(2027, 1, 10),
    }
    for claim_id, approved_at in backdated_approval_times.items():
        db_session.query(ClaimApprovalHistory).filter(
            ClaimApprovalHistory.ClaimID == claim_id,
            ClaimApprovalHistory.Action == HISTORY_APPROVED,
        ).update({ClaimApprovalHistory.ActionDate: approved_at})
    db_session.flush()
    payout_service.recalculate_payout(db_session, eligibility_id)

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    allocations = payout_repository.get_allocations_for_eligibility(db_session, eligibility_id)

    ledger_by_month = {row.PayoutMonth: row for row in ledger}
    assert float(ledger_by_month[date(2026, 9, 1)].ClaimAllocatedAmount) == 9000.00
    assert float(ledger_by_month[date(2026, 9, 1)].ClosingBalance) == 5000.00
    assert float(ledger_by_month[date(2026, 10, 1)].ClaimAllocatedAmount) == 0.0
    assert float(ledger_by_month[date(2026, 10, 1)].ClosingBalance) == 19000.00
    assert float(ledger_by_month[date(2026, 11, 1)].ClaimAllocatedAmount) == 33000.00
    assert float(ledger_by_month[date(2026, 11, 1)].ClosingBalance) == 0.0
    assert float(ledger_by_month[date(2026, 12, 1)].ClaimAllocatedAmount) == 14000.00
    assert float(ledger_by_month[date(2026, 12, 1)].ClosingBalance) == 0.0
    assert float(ledger_by_month[date(2027, 1, 1)].ClaimAllocatedAmount) == 14000.00  # 3000 + 11000
    assert float(ledger_by_month[date(2027, 1, 1)].ClosingBalance) == 0.0
    assert float(ledger_by_month[date(2027, 2, 1)].ClaimAllocatedAmount) == 4000.00
    assert float(ledger_by_month[date(2027, 2, 1)].ClosingBalance) == 10000.00

    claim_b_id = claim_b["claim_id"]
    claim_c_id = claim_c["claim_id"]
    b_allocations = sorted(
        (a.PayoutMonth, float(a.AllocatedAmount), a.AllocationSequence)
        for a in allocations
        if a.ClaimID == claim_b_id
    )
    assert b_allocations == [
        (date(2026, 11, 1), 33000.0, 1),
        (date(2026, 12, 1), 14000.0, 2),
        (date(2027, 1, 1), 3000.0, 3),
    ]
    c_allocations = sorted(
        (a.PayoutMonth, float(a.AllocatedAmount), a.AllocationSequence)
        for a in allocations
        if a.ClaimID == claim_c_id
    )
    assert c_allocations == [
        (date(2027, 1, 1), 11000.0, 1),
        (date(2027, 2, 1), 4000.0, 2),
    ]

    # Full-rebuild sanity check: no stray/duplicate rows from the earlier
    # recomputes triggered automatically during each approval above.
    assert len(allocations) == 1 + 3 + 2  # claim_a + claim_b + claim_c


def test_employee_and_hr_claim_views_show_the_payout_schedule(
    login_as, make_hr_approver, make_employee
) -> None:
    """PAYOUT_REQUIREMENTS.md §16: the employee (and HR) should be able
    to see, on the claim itself, when an approved claim will be paid."""
    claimant = login_as(memp_id=970007, employee_id="97000007", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23), so this claim-approval test isn't affected by
    # that unrelated feature.
    child = _add_child(claimant, "Payout Kid Four", "2024-06-01")
    claim = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-08-01",
        invoice_number="INV-PO-SCHED",
        amount="9000.00",
    )

    before_approval = claimant.get(f"/api/v1/claims/{claim['claim_id']}")
    assert before_approval.status_code == 200
    assert before_approval.json()["payout_schedule"] == []

    make_employee(memp_id=970008, employee_id="97000008", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000008")
    _login_as_existing(claimant, "97000008")
    hr_client = claimant

    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200
    hr_schedule = approve.json()["payout_schedule"]
    assert len(hr_schedule) == 1
    assert float(hr_schedule[0]["allocated_amount"]) == 9000.00

    hr_detail = hr_client.get(f"/api/v1/hr/claims/{claim['claim_id']}")
    assert hr_detail.json()["payout_schedule"] == hr_schedule

    _login_as_existing(claimant, "97000007")
    after_approval = claimant.get(f"/api/v1/claims/{claim['claim_id']}")
    assert after_approval.json()["payout_schedule"] == hr_schedule


def test_rejecting_a_claim_creates_no_payout_rows(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    claimant = login_as(memp_id=970005, employee_id="97000005", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23) — otherwise add_child itself would already
    # populate first-year-payout ledger rows, which this test's "no
    # payout rows at all" assertion isn't about (it's specifically about
    # reject not triggering claim-driven payout persistence).
    child = _add_child(claimant, "Payout Kid Three", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]
    claim = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-08-01",
        invoice_number="INV-PO-REJ",
        amount="1000.00",
    )

    make_employee(memp_id=970006, employee_id="97000006", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000006")
    _login_as_existing(claimant, "97000006")
    hr_client = claimant

    reject = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/reject", json={"remarks": "Not valid"}
    )
    assert reject.status_code == 200

    assert payout_repository.get_ledger_for_eligibility(db_session, eligibility_id) == []
    assert payout_repository.get_allocations_for_eligibility(db_session, eligibility_id) == []
