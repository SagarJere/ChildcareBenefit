"""Eligibility balance tracking tests — first slice of payout tracking.

Per user direction 2026-09-20 (see DECISIONS_LOG.md item 44):
Childcare_EligibilityMaster's ApprovedAmount/UtilizedAmount/
InProgressAmount/RemainingAmount are now maintained balances, recomputed
whenever a claim's status changes in a way that affects them, and HR
cannot approve more than a child's remaining balance for a given
financial year.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import datetime

from fastapi.testclient import TestClient


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def _get_eligibility(client: TestClient, child_id: str, financial_year: str) -> dict:
    response = client.get(
        f"/api/v1/eligibility/{child_id}", params={"financialYear": financial_year}
    )
    rows = response.json()
    assert len(rows) == 1, rows
    return rows[0]


def test_submitting_a_claim_increases_in_progress_amount(login_as) -> None:
    client = login_as(memp_id=960001, employee_id="96000001", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Balance Kid One", "2024-06-01")
    fy = child["eligibility"]["financial_year"]

    before = _get_eligibility(client, child["child_id"], fy)
    assert float(before["in_progress_amount"]) == 0.0

    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BAL-1",
            "invoice_amount": "2000.00",
        },
    ).json()
    client.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    after = _get_eligibility(client, child["child_id"], fy)
    assert float(after["in_progress_amount"]) == 2000.00
    assert float(after["approved_amount"]) == 0.0
    assert float(after["remaining_amount"]) == float(after["allotted_amount"])


def test_approving_a_claim_moves_amount_from_in_progress_to_approved(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=960002, employee_id="96000002", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23), so this claim-approval test isn't affected by
    # that unrelated feature — see DECISIONS_LOG.md's first-year-payout item.
    child = _add_child(claimant, "Balance Kid Two", "2024-06-01")
    fy = child["eligibility"]["financial_year"]
    allotted = float(child["eligibility"]["allotted_amount"])

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BAL-2",
            "invoice_amount": "2000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=960003, employee_id="96000003", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000003")
    _login_as_existing(claimant, "96000003")
    hr_client = claimant

    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "1800.00"}
    )
    assert approve.status_code == 200

    _login_as_existing(claimant, "96000002")
    after = _get_eligibility(claimant, child["child_id"], fy)
    assert float(after["in_progress_amount"]) == 0.0
    assert float(after["approved_amount"]) == 1800.00
    assert float(after["utilized_amount"]) == 1800.00
    assert float(after["remaining_amount"]) == allotted - 1800.00


def test_hr_cannot_approve_more_than_remaining_balance(
    login_as, make_hr_approver, make_employee
) -> None:
    """Even though each individual invoice is within its own amount, HR
    cannot approve a second claim that would push cumulative approved
    amounts for this child+FY over the allotted balance."""
    claimant = login_as(memp_id=960004, employee_id="96000004", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window — see the DOB note on the previous test.
    child = _add_child(claimant, "Balance Kid Three", "2024-06-01")
    allotted = float(child["eligibility"]["allotted_amount"])

    first_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BAL-3A",
            "invoice_amount": str(allotted),
        },
    ).json()
    claimant.post(f"/api/v1/claims/{first_claim['claim_id']}/submit")

    second_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-01",
            "institution_name": "Test Institution",
            "from_date": "2026-09-01",
            "to_date": "2026-09-01",
            "invoice_number": "INV-BAL-3B",
            "invoice_amount": "500.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{second_claim['claim_id']}/submit")

    make_employee(memp_id=960005, employee_id="96000005", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000005")
    _login_as_existing(claimant, "96000005")
    hr_client = claimant

    first_approve = hr_client.post(
        f"/api/v1/hr/claims/{first_claim['claim_id']}/approve",
        json={"approved_amount": str(allotted)},
    )
    assert first_approve.status_code == 200

    second_approve = hr_client.post(
        f"/api/v1/hr/claims/{second_claim['claim_id']}/approve",
        json={"approved_amount": "500.00"},
    )
    assert second_approve.status_code == 400
    assert "remaining balance" in second_approve.json()["message"].lower()


def test_rejecting_a_claim_removes_it_from_in_progress(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=960006, employee_id="96000006", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Balance Kid Four", "2024-06-01")
    fy = child["eligibility"]["financial_year"]

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BAL-4",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=960007, employee_id="96000007", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000007")
    _login_as_existing(claimant, "96000007")
    hr_client = claimant

    hr_client.post(f"/api/v1/hr/claims/{claim['claim_id']}/reject", json={"remarks": "No good"})

    _login_as_existing(claimant, "96000006")
    after = _get_eligibility(claimant, child["child_id"], fy)
    assert float(after["in_progress_amount"]) == 0.0
    assert float(after["approved_amount"]) == 0.0


def test_send_back_removes_from_in_progress_and_resubmit_restores_it(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=960008, employee_id="96000008", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Balance Kid Five", "2024-06-01")
    fy = child["eligibility"]["financial_year"]

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BAL-5",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=960009, employee_id="96000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000009")
    _login_as_existing(claimant, "96000009")
    hr_client = claimant

    hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/send-back", json={"remarks": "Fix invoice number"}
    )

    _login_as_existing(claimant, "96000008")
    after_sendback = _get_eligibility(claimant, child["child_id"], fy)
    assert float(after_sendback["in_progress_amount"]) == 0.0

    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    after_resubmit = _get_eligibility(claimant, child["child_id"], fy)
    assert float(after_resubmit["in_progress_amount"]) == 1000.00
