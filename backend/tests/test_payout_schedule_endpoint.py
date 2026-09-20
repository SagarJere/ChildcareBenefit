"""Aggregate monthly payout ledger endpoint — Increment 4
(PAYOUT_REQUIREMENTS.md §16, child+financial-year level, as opposed to
ClaimResponse.payout_schedule which is scoped to one claim).

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


def test_payout_schedule_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get(
        "/api/v1/eligibility/some_child_1/payout-schedule", params={"financialYear": "2026-27"}
    )
    assert response.status_code == 401


def test_payout_schedule_returns_404_for_unknown_financial_year(login_as) -> None:
    client = login_as(memp_id=980001, employee_id="98000001", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Ledger Kid One", "2026-03-01")

    response = client.get(
        f"/api/v1/eligibility/{child['child_id']}/payout-schedule",
        params={"financialYear": "1999-00"},
    )
    assert response.status_code == 404


def test_payout_schedule_is_scoped_to_own_children(login_as, make_employee) -> None:
    client = login_as(memp_id=980002, employee_id="98000002", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Ledger Kid Two", "2026-03-01")
    fy = child["eligibility"]["financial_year"]

    make_employee(memp_id=980003, employee_id="98000003", Joindate=datetime(2018, 1, 1))
    other_login = client.post("/api/v1/auth/login", json={"employee_id": "98000003"})
    client.headers.update({"Authorization": f"Bearer {other_login.json()['access_token']}"})

    response = client.get(
        f"/api/v1/eligibility/{child['child_id']}/payout-schedule", params={"financialYear": fy}
    )
    assert response.status_code == 404


def test_payout_schedule_shows_full_ledger_including_zero_months(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=980004, employee_id="98000004", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Ledger Kid Three", "2026-03-01")
    fy = child["eligibility"]["financial_year"]
    allotted_months = child["eligibility"]["eligible_months"]

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-LEDGER-1",
            "invoice_amount": "9000.00",
        },
    ).json()
    submit = claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert submit.status_code == 200

    make_employee(memp_id=980005, employee_id="98000005", Joindate=datetime(2018, 1, 1))
    make_hr_approver("98000005")
    _login_as_existing(claimant, "98000005")
    hr_client = claimant

    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    _login_as_existing(claimant, "98000004")
    schedule = claimant.get(
        f"/api/v1/eligibility/{child['child_id']}/payout-schedule", params={"financialYear": fy}
    )
    assert schedule.status_code == 200
    rows = schedule.json()

    assert len(rows) == allotted_months
    total_allocated = sum(float(row["claim_allocated_amount"]) for row in rows)
    assert total_allocated == 9000.00
    total_entitlement = sum(float(row["entitlement_amount"]) for row in rows)
    assert total_entitlement == allotted_months * 14000.0
    # Every row is well-formed even where nothing was allocated.
    for row in rows:
        assert float(row["closing_balance"]) == (
            float(row["total_available_amount"])
            - float(row["claim_allocated_amount"])
            - float(row["adjustment_amount"])
        )
        assert float(row["adjustment_amount"]) == 0.0
