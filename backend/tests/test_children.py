"""Child Management + Eligibility integration tests (Increment 3).

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import date, datetime

from fastapi.testclient import TestClient


def test_add_child_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.post(
        "/api/v1/children", json={"child_name": "Aarav", "child_dob": "2023-01-01"}
    )

    assert response.status_code == 401


def test_add_child_rejects_future_dob(login_as) -> None:
    client = login_as(memp_id=910001, employee_id="91000001")

    response = client.post(
        "/api/v1/children", json={"child_name": "Aarav", "child_dob": "2099-01-01"}
    )

    assert response.status_code == 422


def test_add_child_rejects_blank_name(login_as) -> None:
    client = login_as(memp_id=910002, employee_id="91000002")

    response = client.post("/api/v1/children", json={"child_name": "", "child_dob": "2023-01-01"})

    assert response.status_code == 422


def test_add_child_fails_when_join_date_missing(login_as) -> None:
    client = login_as(memp_id=910003, employee_id="91000003", Joindate=None)

    response = client.post(
        "/api/v1/children", json={"child_name": "Aarav", "child_dob": "2023-01-01"}
    )

    assert response.status_code == 400
    assert "join date" in response.json()["message"].lower()


def test_add_child_creates_child_and_eligibility_atomically(login_as) -> None:
    client = login_as(memp_id=910004, employee_id="91000004", Joindate=datetime(2018, 1, 1))

    response = client.post(
        "/api/v1/children", json={"child_name": "Aarav Mehta", "child_dob": "2023-06-01"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["child_id"] == "91000004_1"
    assert body["employee_id"] == "91000004"
    assert body["child_sequence_no"] == 1
    assert body["child_name"] == "Aarav Mehta"
    assert body["child_dob"] == "2023-06-01"

    eligibility = body["eligibility"]
    assert eligibility is not None
    assert eligibility["child_id"] == "91000004_1"
    assert float(eligibility["monthly_benefit_amount"]) == 14000.0
    assert float(eligibility["utilized_amount"]) == 0.0
    assert eligibility["remaining_amount"] == eligibility["allotted_amount"]


def test_second_child_gets_sequence_two(login_as) -> None:
    client = login_as(memp_id=910005, employee_id="91000005", Joindate=datetime(2018, 1, 1))

    first = client.post(
        "/api/v1/children", json={"child_name": "Child One", "child_dob": "2020-01-01"}
    )
    second = client.post(
        "/api/v1/children", json={"child_name": "Child Two", "child_dob": "2022-01-01"}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["child_id"] == "91000005_1"
    assert second.json()["child_id"] == "91000005_2"


def test_third_child_is_rejected(login_as) -> None:
    client = login_as(memp_id=910006, employee_id="91000006", Joindate=datetime(2018, 1, 1))

    client.post("/api/v1/children", json={"child_name": "Child One", "child_dob": "2020-01-01"})
    client.post("/api/v1/children", json={"child_name": "Child Two", "child_dob": "2021-01-01"})
    third = client.post(
        "/api/v1/children", json={"child_name": "Child Three", "child_dob": "2022-01-01"}
    )

    assert third.status_code == 400
    assert "maximum" in third.json()["message"].lower()


def test_list_children_returns_only_own_children(login_as) -> None:
    client_a = login_as(memp_id=910007, employee_id="91000007", Joindate=datetime(2018, 1, 1))
    client_a.post("/api/v1/children", json={"child_name": "Child A", "child_dob": "2020-01-01"})

    listing = client_a.get("/api/v1/children")

    assert listing.status_code == 200
    children = listing.json()
    assert len(children) == 1
    assert children[0]["child_name"] == "Child A"
    assert children[0]["eligibility"] is not None


def test_children_are_isolated_between_employees(login_as, make_employee) -> None:
    client = login_as(memp_id=910008, employee_id="91000008", Joindate=datetime(2018, 1, 1))
    client.post("/api/v1/children", json={"child_name": "Owned Child", "child_dob": "2020-01-01"})

    # Log in as a second employee using the SAME TestClient instance —
    # its stored token is now the second employee's.
    make_employee(memp_id=910009, employee_id="91000009", Joindate=datetime(2018, 1, 1))
    login_response = client.post("/api/v1/auth/login", json={"employee_id": "91000009"})
    client.headers.update({"Authorization": f"Bearer {login_response.json()['access_token']}"})

    listing = client.get("/api/v1/children")

    assert listing.status_code == 200
    assert listing.json() == []


def test_get_child_by_id_not_found_for_other_employees_child(login_as, make_employee) -> None:
    owner = login_as(memp_id=910010, employee_id="91000010", Joindate=datetime(2018, 1, 1))
    created = owner.post(
        "/api/v1/children", json={"child_name": "Owned Child", "child_dob": "2020-01-01"}
    )
    child_id = created.json()["child_id"]

    make_employee(memp_id=910011, employee_id="91000011", Joindate=datetime(2018, 1, 1))
    login_response = owner.post("/api/v1/auth/login", json={"employee_id": "91000011"})
    owner.headers.update({"Authorization": f"Bearer {login_response.json()['access_token']}"})

    response = owner.get(f"/api/v1/children/{child_id}")

    assert response.status_code == 404


def test_preview_eligibility_does_not_persist_anything(login_as) -> None:
    client = login_as(memp_id=910012, employee_id="91000012", Joindate=datetime(2018, 1, 1))

    preview = client.post("/api/v1/children/preview-eligibility", json={"child_dob": "2023-06-01"})

    assert preview.status_code == 200
    body = preview.json()
    assert body["eligible_months"] > 0
    assert "child_id" not in body

    listing = client.get("/api/v1/children")
    assert listing.json() == []


def test_eligibility_endpoints_return_created_record(login_as) -> None:
    """A child well under six gets both the current AND next financial
    year's eligibility record by default (see DECISIONS_LOG.md item 43)."""
    client = login_as(memp_id=910013, employee_id="91000013", Joindate=datetime(2018, 1, 1))
    created = client.post(
        "/api/v1/children", json={"child_name": "Aarav", "child_dob": "2023-06-01"}
    )
    child_id = created.json()["child_id"]

    all_eligibility = client.get("/api/v1/eligibility")
    assert all_eligibility.status_code == 200
    assert len(all_eligibility.json()) == 2

    by_child = client.get(f"/api/v1/eligibility/{child_id}")
    assert by_child.status_code == 200
    assert len(by_child.json()) == 2
    assert all(row["child_id"] == child_id for row in by_child.json())

    fy = created.json()["eligibility"]["financial_year"]
    filtered = client.get(f"/api/v1/eligibility/{child_id}", params={"financialYear": fy})
    assert len(filtered.json()) == 1

    filtered_other_fy = client.get(
        f"/api/v1/eligibility/{child_id}", params={"financialYear": "1999-00"}
    )
    assert filtered_other_fy.json() == []


def test_add_child_also_creates_next_financial_year_eligibility(login_as) -> None:
    from datetime import date as date_cls

    from app.services import eligibility_calculator

    client = login_as(memp_id=910015, employee_id="91000015", Joindate=datetime(2018, 1, 1))
    created = client.post(
        "/api/v1/children", json={"child_name": "Diya", "child_dob": "2023-06-01"}
    )
    child_id = created.json()["child_id"]
    current_fy = created.json()["eligibility"]["financial_year"]

    current_fy_window = eligibility_calculator.compute_financial_year(date_cls.today())
    next_fy_window = eligibility_calculator.next_financial_year_window(current_fy_window)

    rows = client.get(f"/api/v1/eligibility/{child_id}").json()
    financial_years = {row["financial_year"] for row in rows}
    assert financial_years == {current_fy, next_fy_window.label}
    assert current_fy == current_fy_window.label

    next_fy_row = next(r for r in rows if r["financial_year"] == next_fy_window.label)
    assert next_fy_row["eligibility_start_date"] == next_fy_window.start_date.isoformat()
    assert next_fy_row["eligible_months"] == 12
    assert float(next_fy_row["allotted_amount"]) == 12 * 14000.0


def test_add_child_skips_next_financial_year_when_six_year_cutoff_is_this_fy(login_as) -> None:
    """Per user direction 2026-09-20: if the child's 72nd month (six-year
    cutoff) already falls within the current financial year, no next-FY
    eligibility record is created since it would be zero anyway."""
    from datetime import date as date_cls

    from app.services import eligibility_calculator

    current_fy_window = eligibility_calculator.compute_financial_year(date_cls.today())
    # A DOB whose 6th birthday falls exactly on the current FY's start
    # month (April) — within the current FY, so the cutoff is this year.
    child_dob = date_cls(current_fy_window.start_date.year - 6, 4, 1)

    client = login_as(memp_id=910016, employee_id="91000016", Joindate=datetime(2018, 1, 1))
    created = client.post(
        "/api/v1/children", json={"child_name": "Vihaan", "child_dob": child_dob.isoformat()}
    )
    child_id = created.json()["child_id"]

    rows = client.get(f"/api/v1/eligibility/{child_id}").json()
    assert len(rows) == 1
    assert rows[0]["financial_year"] == current_fy_window.label


def test_eligibility_calculation_matches_pure_calculator(login_as) -> None:
    from app.services.eligibility_calculator import calculate_eligibility

    join_date = date(2018, 1, 1)
    child_dob = date(2023, 6, 1)
    join_datetime = datetime.combine(join_date, datetime.min.time())
    client = login_as(memp_id=910014, employee_id="91000014", Joindate=join_datetime)

    created = client.post(
        "/api/v1/children", json={"child_name": "Aarav", "child_dob": child_dob.isoformat()}
    )

    expected = calculate_eligibility(
        employee_join_date=join_date, child_dob=child_dob, as_of=date.today()
    )
    eligibility = created.json()["eligibility"]
    assert eligibility["financial_year"] == expected.financial_year
    assert eligibility["eligibility_start_date"] == expected.eligibility_start_date.isoformat()
    assert eligibility["eligible_months"] == expected.eligible_months
    assert float(eligibility["allotted_amount"]) == float(expected.allotted_amount)
