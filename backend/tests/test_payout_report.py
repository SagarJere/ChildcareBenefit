"""HR Payout Report tests — the pivoted Apr-Mar view over
Childcare_PayoutMonthlyLedger (PAYOUT_REQUIREMENTS.md §9), filterable by
financial year, employee, and child.

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


def test_payout_report_requires_hr_authorization(login_as) -> None:
    client = login_as(memp_id=990001, employee_id="99000001", Joindate=datetime(2018, 1, 1))

    assert client.get("/api/v1/hr/reports/payout").status_code == 403


def test_payout_report_is_empty_with_no_approved_claims(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=990002, employee_id="99000002", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23) — otherwise add_child itself would already
    # populate first-year-payout ledger rows, and this report (until
    # Increment 4 splits it) shows all payout regardless of source, so
    # "empty with no claims" would no longer hold.
    _add_child(claimant, "Report Payout Kid Zero", "2024-06-01")

    make_employee(memp_id=990003, employee_id="99000003", Joindate=datetime(2018, 1, 1))
    make_hr_approver("99000003")
    _login_as_existing(claimant, "99000003")

    response = claimant.get(
        "/api/v1/hr/reports/payout", params={"employee_id": "99000002"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert float(body["totals"]["total_payout"]) == 0.0


def test_payout_report_shows_apr_to_mar_breakdown_and_supports_filters(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=990004, employee_id="99000004", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Payout Kid One", "2024-06-01")
    fy = child["eligibility"]["financial_year"]

    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-PAYOUT-RPT-1",
            "invoice_amount": "9000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=990005, employee_id="99000005", Joindate=datetime(2018, 1, 1))
    make_hr_approver("99000005")
    _login_as_existing(claimant, "99000005")
    hr_client = claimant

    approve = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "9000.00"}
    )
    assert approve.status_code == 200

    report = hr_client.get(
        "/api/v1/hr/reports/payout",
        params={"employee_id": "99000004", "financial_year": fy},
    )
    assert report.status_code == 200
    body = report.json()
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["employee_id"] == "99000004"
    assert row["child_id"] == child["child_id"]
    assert row["child_name"] == "Report Payout Kid One"
    assert row["child_dob"] == "2024-06-01"
    assert row["financial_year"] == fy
    months = ("apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "jan", "feb", "mar")
    month_total = sum(float(row[m]) for m in months)
    assert month_total == 9000.00
    assert float(row["total_payout"]) == 9000.00
    assert float(body["totals"]["total_payout"]) == 9000.00

    # Filtering by a different child excludes this row.
    other_child_filter = hr_client.get(
        "/api/v1/hr/reports/payout", params={"child_id": "nonexistent_child_1"}
    )
    assert other_child_filter.json()["rows"] == []

    # Filtering by the wrong financial year excludes this row too.
    wrong_fy_filter = hr_client.get(
        "/api/v1/hr/reports/payout", params={"financial_year": "1999-00"}
    )
    assert wrong_fy_filter.json()["rows"] == []


def test_payout_report_csv_format(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=990006, employee_id="99000006", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Payout Kid Two", "2024-06-01")
    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-PAYOUT-RPT-2",
            "invoice_amount": "5000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=990007, employee_id="99000007", Joindate=datetime(2018, 1, 1))
    make_hr_approver("99000007")
    _login_as_existing(claimant, "99000007")
    hr_client = claimant

    hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "5000.00"}
    )

    response = hr_client.get(
        "/api/v1/hr/reports/payout",
        params={"employee_id": "99000006", "format": "csv"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "child_name" in response.text
    assert "Report Payout Kid Two" in response.text


def test_employee_payout_report_is_scoped_to_own_children(
    login_as, make_hr_approver, make_employee
) -> None:
    """The employee-facing GET /eligibility/payout-report reuses the same
    service as HR's report but must never expose another employee's
    data, and must not require (or accept) an employee filter."""
    claimant = login_as(memp_id=990008, employee_id="99000008", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Payout Kid Three", "2024-06-01")
    fy = child["eligibility"]["financial_year"]
    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-PAYOUT-RPT-3",
            "invoice_amount": "7000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=990009, employee_id="99000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("99000009")
    _login_as_existing(claimant, "99000009")
    hr_client = claimant
    hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "7000.00"}
    )

    # A different employee sees nothing for this child.
    make_employee(memp_id=990010, employee_id="99000010", Joindate=datetime(2018, 1, 1))
    _login_as_existing(claimant, "99000010")
    other_view = claimant.get("/api/v1/eligibility/payout-report")
    assert other_view.status_code == 200
    assert other_view.json()["rows"] == []

    # The owning employee sees their own row, scoped correctly.
    _login_as_existing(claimant, "99000008")
    own_view = claimant.get("/api/v1/eligibility/payout-report", params={"financial_year": fy})
    assert own_view.status_code == 200
    rows = own_view.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["employee_id"] == "99000008"
    assert rows[0]["child_id"] == child["child_id"]
    assert rows[0]["child_dob"] == "2024-06-01"
    assert float(rows[0]["total_payout"]) == 7000.00


def test_employee_payout_report_csv_format(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=990011, employee_id="99000011", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Payout Kid Four", "2024-06-01")
    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-PAYOUT-RPT-4",
            "invoice_amount": "3000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=990012, employee_id="99000012", Joindate=datetime(2018, 1, 1))
    make_hr_approver("99000012")
    _login_as_existing(claimant, "99000012")
    hr_client = claimant
    hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "3000.00"}
    )

    _login_as_existing(claimant, "99000011")
    response = claimant.get("/api/v1/eligibility/payout-report", params={"format": "csv"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "child_name" in response.text
    assert "Report Payout Kid Four" in response.text
