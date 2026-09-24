"""Employee-facing eligibility endpoint tests, including the kid-wise,
financial-year-wise eligibility report (post-Increment-7 improvement).

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


def test_eligibility_report_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get("/api/v1/eligibility/report")

    assert response.status_code == 401


def test_eligibility_report_is_scoped_to_own_children(login_as, make_employee) -> None:
    client = login_as(memp_id=950001, employee_id="95000001", Joindate=datetime(2018, 1, 1))
    _add_child(client, "Report Kid One", "2026-03-01")

    make_employee(memp_id=950002, employee_id="95000002", Joindate=datetime(2018, 1, 1))
    other_login = client.post("/api/v1/auth/login", json={"employee_id": "95000002"})
    client.headers.update({"Authorization": f"Bearer {other_login.json()['access_token']}"})

    report = client.get("/api/v1/eligibility/report")
    assert report.status_code == 200
    assert report.json()["rows"] == []


def test_eligibility_report_shows_utilized_in_progress_balance_and_last_modified(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=950003, employee_id="95000003", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23), so this claim-approval test isn't affected by
    # that unrelated feature.
    child = _add_child(claimant, "Report Kid Two", "2024-06-01")

    approved_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-ER-1",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{approved_claim['claim_id']}/submit")

    pending_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-01",
            "institution_name": "Test Institution",
            "from_date": "2026-09-01",
            "to_date": "2026-09-01",
            "invoice_number": "INV-ER-2",
            "invoice_amount": "500.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{pending_claim['claim_id']}/submit")

    make_employee(memp_id=950004, employee_id="95000004", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000004")
    _login_as_existing(claimant, "95000004")
    hr_client = claimant

    hr_client.post(
        f"/api/v1/hr/claims/{approved_claim['claim_id']}/approve",
        json={"approved_amount": "800.00"},
    )

    _login_as_existing(claimant, "95000003")
    report = claimant.get("/api/v1/eligibility/report")

    assert report.status_code == 200
    rows = report.json()["rows"]
    # Per DECISIONS_LOG.md item 43, the child also got a next-financial-year
    # eligibility row by default — the claims/approval only affect the
    # current FY's row, so find that one rather than assuming a single row.
    from app.services.eligibility_calculator import compute_financial_year

    current_fy = compute_financial_year(datetime.now().date()).label
    assert len(rows) == 2
    row = next(r for r in rows if r["financial_year"] == current_fy)
    assert row["child_id"] == child["child_id"]
    assert row["child_name"] == "Report Kid Two"
    assert row["child_dob"] == "2024-06-01"
    assert float(row["utilized_amount"]) == 800.00
    assert float(row["in_progress_amount"]) == 500.00
    assert float(row["balance_amount"]) == float(row["allotted_amount"]) - 800.00
    assert row["last_modified_date"] is not None


def test_eligibility_report_route_is_not_shadowed_by_child_id_route(login_as) -> None:
    """`/eligibility/report` must resolve to the report endpoint, not be
    swallowed by `/eligibility/{child_id}` with child_id="report"."""
    client = login_as(memp_id=950005, employee_id="95000005", Joindate=datetime(2018, 1, 1))

    response = client.get("/api/v1/eligibility/report")

    assert response.status_code == 200
    assert "rows" in response.json()
