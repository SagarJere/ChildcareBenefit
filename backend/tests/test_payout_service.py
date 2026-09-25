"""Payout persistence tests — Increment 2 (PAYOUT_REQUIREMENTS.md).

Verifies that approving a claim actually persists the correct
Childcare_PayoutMonthlyLedger / Childcare_PayoutAllocation rows via
app/services/payout_service.recalculate_payout, wired into
hr_service.approve_claim. The calculation logic itself is already
exhaustively unit-tested in test_payout_calculator.py — these tests
focus on the database wiring: full-rebuild across multiple approvals,
and that rejecting/sending back a claim does not create payout rows.

Payout allocation is anchored to the HR *approval* timestamp, not the
claim's invoice date (PAYOUT_REQUIREMENTS.md §5), and — as of user
direction 2026-09-25 — the submission's own cutoff-adjusted month, if
that's later (see payout_calculator._effective_processing_month), unless
HR's ForceSameMonthPayout override is on (same day's follow-up feature),
in which case the cutoff-adjusted month is ignored entirely. So to
exercise cross-month spillover deterministically, the multi-claim test
below directly backdates both Childcare_ClaimApprovalHistory.ActionDate
and Childcare_ClaimMaster.SubmittedDate (the same "insert synthetic
precondition rows directly" pattern test_claims.py already uses for
attachments) and re-triggers the recompute, since three real submissions
and approvals made seconds apart in a test run would otherwise all land
in the same real calendar month (and, without also backdating
SubmittedDate, today's real submission date would push every claim's
effective month later than intended once the cutoff day applies).

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""

from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.claim import ClaimMaster
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


def test_payout_settings_cutoff_day_actually_wired_through_recalculate(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    """End-to-end (settings -> claim submission snapshot -> payout_service
    -> payout_repository -> payout_calculator), not just the pure
    calculator math already covered by test_payout_calculator.py's
    TestSubmissionCutoffDay. "Today" is 2026-09-25 — past the *default*
    cutoff day (5, see conftest's client_with_db reset), which would
    otherwise push this claim to October regardless of whether this test
    ever touched the settings endpoint at all. HR raises the cutoff to 28
    *before* the claim is submitted; since the cutoff day that applies to
    a claim is the one snapshotted onto it at the moment it's actually
    submitted (ClaimMaster.SubmissionCutoffDayAtSubmission — user-
    reported bug 2026-09-25, changing the setting must never retroactively
    move an already-submitted claim), the claim should land in September
    instead, proving the setting genuinely reaches the calculation and
    isn't just coincidentally matching the default."""
    make_employee(memp_id=970006, employee_id="97000006", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000006")

    claimant = login_as(memp_id=970005, employee_id="97000005", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Payout Kid Three", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    _login_as_existing(claimant, "97000006")
    settings = claimant.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 28,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert settings.status_code == 200

    _login_as_existing(claimant, "97000005")
    claim = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-01",
        invoice_number="INV-PO-CUTOFF",
        amount="9000.00",
    )

    _login_as_existing(claimant, "97000006")
    approve = claimant.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    ledger = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    ledger_by_month = {row.PayoutMonth: row for row in ledger}
    assert float(ledger_by_month[date(2026, 9, 1)].ClaimAllocatedAmount) == 9000.00
    assert float(ledger_by_month[date(2026, 10, 1)].ClaimAllocatedAmount) == 0.0


def test_changing_cutoff_day_after_submission_does_not_move_an_approved_claim(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    """End-to-end regression for the exact bug the user reported
    2026-09-25: a claim submitted+approved while the cutoff day was
    generous (28) correctly lands in September; HR then lowers the
    cutoff to 20 and a second claim is submitted+approved — the *first*
    claim's month must not shift just because the setting changed and a
    later approval triggered a fresh full-rebuild recompute for the same
    eligibility."""
    make_employee(memp_id=970009, employee_id="97000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000009")

    claimant = login_as(memp_id=970010, employee_id="97000010", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Payout Kid Five", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    _login_as_existing(claimant, "97000009")
    first_settings = claimant.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 28,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert first_settings.status_code == 200

    _login_as_existing(claimant, "97000010")
    claim_a = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-01",
        invoice_number="INV-PO-CUTOFF-A",
        amount="10000.00",
    )

    _login_as_existing(claimant, "97000009")
    approve_a = claimant.post(
        f"/api/v1/hr/claims/{claim_a['claim_id']}/approve", json={"approved_amount": "10000.00"}
    )
    assert approve_a.status_code == 200

    ledger_after_a = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    by_month_after_a = {row.PayoutMonth: row for row in ledger_after_a}
    assert float(by_month_after_a[date(2026, 9, 1)].ClaimAllocatedAmount) == 10000.00

    second_settings = claimant.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 20,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert second_settings.status_code == 200

    _login_as_existing(claimant, "97000010")
    claim_b = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-02",
        invoice_number="INV-PO-CUTOFF-B",
        amount="5000.00",
    )

    _login_as_existing(claimant, "97000009")
    approve_b = claimant.post(
        f"/api/v1/hr/claims/{claim_b['claim_id']}/approve", json={"approved_amount": "5000.00"}
    )
    assert approve_b.status_code == 200

    ledger_after_b = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    by_month_after_b = {row.PayoutMonth: row for row in ledger_after_b}
    # Claim A stays in September — the cutoff day it was actually
    # submitted under (28) is frozen on the claim itself, not re-derived
    # from whatever the setting has since changed to.
    assert float(by_month_after_b[date(2026, 9, 1)].ClaimAllocatedAmount) == 10000.00
    # Claim B correctly lands in October under the new, stricter cutoff.
    assert float(by_month_after_b[date(2026, 10, 1)].ClaimAllocatedAmount) == 5000.00


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
    # timestamps from the loop above. SubmittedDate is backdated to the
    # 1st of that same month, so its cutoff-adjusted month never lands
    # later than the approval month and this test stays purely about
    # approval-time-driven allocation, unrelated to the cutoff-day
    # feature (which has its own dedicated tests).
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
        db_session.query(ClaimMaster).filter(ClaimMaster.ClaimID == claim_id).update(
            {ClaimMaster.SubmittedDate: datetime(approved_at.year, approved_at.month, 1)}
        )
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


def test_force_same_month_payout_is_read_live_and_sweeps_an_already_approved_claim(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    """The deliberate opposite of the cutoff-day snapshot fix (item 76):
    ForceSameMonthPayout is read live on every recompute, not fixed at
    submission time. A claim submitted after the cutoff day defers to
    next month as usual; HR then turns the override on (for FY close-
    out) and triggers a fresh recompute — the already-approved claim
    must be swept into its approval month immediately, not stay pinned
    to where the cutoff rule originally put it. That's the whole point:
    HR wants everything currently in flight cleared out, not just
    claims submitted from then on (user direction 2026-09-25)."""
    make_employee(memp_id=970012, employee_id="97000012", Joindate=datetime(2018, 1, 1))
    make_hr_approver("97000012")

    claimant = login_as(memp_id=970011, employee_id="97000011", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Payout Kid Seven", "2024-06-01")
    eligibility_id = child["eligibility"]["eligibility_id"]

    _login_as_existing(claimant, "97000012")
    baseline = claimant.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 5,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert baseline.status_code == 200

    _login_as_existing(claimant, "97000011")
    claim = _create_and_submit_claim(
        claimant,
        child["child_id"],
        invoice_date="2026-06-01",
        invoice_number="INV-FORCE-SAME-MONTH",
        amount="9000.00",
    )

    _login_as_existing(claimant, "97000012")
    approve = claimant.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    # "Today" is 2026-09-25, after the default cutoff day (5), so this
    # claim defers to October despite being approved in September.
    ledger_before = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    by_month_before = {row.PayoutMonth: row for row in ledger_before}
    assert float(by_month_before[date(2026, 9, 1)].ClaimAllocatedAmount) == 0.0
    assert float(by_month_before[date(2026, 10, 1)].ClaimAllocatedAmount) == 9000.00

    turn_on = claimant.put(
        "/api/v1/hr/payout-settings",
        json={"submission_cutoff_day": 5, "claims_blocked": False, "force_same_month_payout": True},
    )
    assert turn_on.status_code == 200

    # In practice a later claim's own approval would trigger this full
    # rebuild; called directly here to isolate the override's effect
    # from needing a second claim.
    payout_service.recalculate_payout(db_session, eligibility_id)

    ledger_after = payout_repository.get_ledger_for_eligibility(db_session, eligibility_id)
    by_month_after = {row.PayoutMonth: row for row in ledger_after}
    assert float(by_month_after[date(2026, 9, 1)].ClaimAllocatedAmount) == 9000.00
    assert float(by_month_after[date(2026, 10, 1)].ClaimAllocatedAmount) == 0.0
