"""HR Reports integration tests (Increment 6).

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


def test_reports_require_hr_authorization(login_as) -> None:
    client = login_as(memp_id=940001, employee_id="94000001", Joindate=datetime(2018, 1, 1))

    assert client.get("/api/v1/hr/reports/claims-summary").status_code == 403
    assert client.get("/api/v1/hr/reports/eligibility-utilization").status_code == 403
    assert client.get("/api/v1/hr/reports/headcount").status_code == 403


def test_claims_summary_reflects_filters_and_totals(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=940002, employee_id="94000002", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Kid One", "2026-03-01")

    claim_a = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-R-1",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim_a['claim_id']}/submit")

    claim_b = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-01",
            "invoice_number": "INV-R-2",
            "invoice_amount": "500.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim_b['claim_id']}/submit")

    make_employee(memp_id=940003, employee_id="94000003", Joindate=datetime(2018, 1, 1))
    make_hr_approver("94000003")
    _login_as_existing(claimant, "94000003")
    hr_client = claimant

    hr_client.post(
        f"/api/v1/hr/claims/{claim_a['claim_id']}/approve", json={"approved_amount": "900.00"}
    )

    all_report = hr_client.get("/api/v1/hr/reports/claims-summary")
    assert all_report.status_code == 200
    body = all_report.json()
    claim_ids_in_report = {row["claim_id"] for row in body["rows"]}
    assert claim_a["claim_id"] in claim_ids_in_report
    assert claim_b["claim_id"] in claim_ids_in_report
    assert body["totals"]["count_by_status"]["Approved"] >= 1
    assert body["totals"]["count_by_status"]["Submitted"] >= 1
    assert float(body["totals"]["total_approved_amount"]) >= 900.00

    row_a = next(row for row in body["rows"] if row["claim_id"] == claim_a["claim_id"])
    row_b = next(row for row in body["rows"] if row["claim_id"] == claim_b["claim_id"])
    assert row_a["submitted_date"] is not None
    assert row_a["approved_date"] is not None
    assert row_b["submitted_date"] is not None
    assert row_b["approved_date"] is None

    date_filtered = hr_client.get(
        "/api/v1/hr/reports/claims-summary",
        params={"date_from": "2026-09-01", "date_to": "2026-09-01"},
    )
    filtered_ids = {row["claim_id"] for row in date_filtered.json()["rows"]}
    assert claim_b["claim_id"] in filtered_ids
    assert claim_a["claim_id"] not in filtered_ids

    status_filtered = hr_client.get(
        "/api/v1/hr/reports/claims-summary", params={"status": "Approved"}
    )
    assert all(row["claim_status"] == "Approved" for row in status_filtered.json()["rows"])


def test_claims_summary_csv_format(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=940004, employee_id="94000004", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Kid Two", "2026-03-01")
    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-R-3",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=940005, employee_id="94000005", Joindate=datetime(2018, 1, 1))
    make_hr_approver("94000005")
    _login_as_existing(claimant, "94000005")
    hr_client = claimant

    response = hr_client.get("/api/v1/hr/reports/claims-summary", params={"format": "csv"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "claim_id" in response.text
    assert "INV-R-3" in response.text


def test_eligibility_utilization_computes_live_totals(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=940006, employee_id="94000006", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Report Kid Three", "2026-03-01")

    approved_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-R-4",
            "invoice_amount": "1000.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{approved_claim['claim_id']}/submit")

    pending_claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-09-01",
            "invoice_number": "INV-R-5",
            "invoice_amount": "500.00",
        },
    ).json()
    claimant.post(f"/api/v1/claims/{pending_claim['claim_id']}/submit")

    make_employee(memp_id=940007, employee_id="94000007", Joindate=datetime(2018, 1, 1))
    make_hr_approver("94000007")
    _login_as_existing(claimant, "94000007")
    hr_client = claimant

    hr_client.post(
        f"/api/v1/hr/claims/{approved_claim['claim_id']}/approve",
        json={"approved_amount": "800.00"},
    )

    # Per DECISIONS_LOG.md item 43, the child also got a next-financial-year
    # eligibility row by default — filter to the current FY (where the
    # claims actually are) rather than assuming a single row.
    from app.services.eligibility_calculator import compute_financial_year

    current_fy = compute_financial_year(datetime.now().date()).label

    report = hr_client.get(
        "/api/v1/hr/reports/eligibility-utilization",
        params={"employee_id": "94000006", "financial_year": current_fy},
    )
    assert report.status_code == 200
    body = report.json()
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert float(row["approved_amount"]) == 800.00
    assert float(row["in_progress_amount"]) == 500.00
    assert float(row["remaining_after_approved"]) == float(row["allotted_amount"]) - 800.00


def test_headcount_report_counts_children_correctly(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=940008, employee_id="94000008", Joindate=datetime(2018, 1, 1))
    _add_child(claimant, "Report Kid Four", "2026-03-01")
    _add_child(claimant, "Report Kid Five", "2020-06-01")

    make_employee(memp_id=940009, employee_id="94000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("94000009")
    _login_as_existing(claimant, "94000009")
    hr_client = claimant

    report = hr_client.get("/api/v1/hr/reports/headcount")

    assert report.status_code == 200
    body = report.json()
    assert body["total_children"] >= 2
    assert body["total_employees_with_children"] >= 1
    assert body["employees_with_two_children"] >= 1
    fy_labels = {entry["financial_year"] for entry in body["by_financial_year"]}
    assert "2026-27" in fy_labels
    age_brackets = {entry["age_bracket"] for entry in body["by_age_bracket"]}
    assert age_brackets == {"0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6+"}


def test_headcount_csv_format(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=940010, employee_id="94000010", Joindate=datetime(2018, 1, 1))
    _add_child(claimant, "Report Kid Six", "2026-03-01")

    make_employee(memp_id=940011, employee_id="94000011", Joindate=datetime(2018, 1, 1))
    make_hr_approver("94000011")
    _login_as_existing(claimant, "94000011")
    hr_client = claimant

    response = hr_client.get("/api/v1/hr/reports/headcount", params={"format": "csv"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "metric,value" in response.text
    assert "total_children" in response.text
