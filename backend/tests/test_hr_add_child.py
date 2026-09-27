"""HR adding a child on behalf of another employee (user direction
2026-09-26) — Increment 1 of the HR-add-child feature. Reuses
child_service.add_child entirely, so the 2-child cap/duplicate-check/
eligibility-calculation rules are already exhaustively covered by
test_children.py; these tests focus on what's new here: the HR-only
endpoint, acting on an arbitrary target employee, and recording the
acting HR user (not the target employee) as CreatedBy.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.child import ChildMaster


def test_hr_add_child_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000001", "child_name": "Aarav", "child_dob": "2023-01-01"},
    )
    assert response.status_code == 401


def test_hr_add_child_requires_hr(login_as, make_employee) -> None:
    make_employee(memp_id=960001, employee_id="96000001", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=960002, employee_id="96000002", Joindate=datetime(2018, 1, 1))

    response = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000001", "child_name": "Aarav", "child_dob": "2023-01-01"},
    )
    assert response.status_code == 403


def test_hr_add_child_for_employee_records_hr_user_as_created_by(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    make_employee(memp_id=960003, employee_id="96000003", Joindate=datetime(2018, 1, 1))

    client = login_as(memp_id=960004, employee_id="96000004", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000004")

    response = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000003", "child_name": "Aarav Mehta", "child_dob": "2023-06-01"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["child_id"] == "96000003_1"
    assert body["employee_id"] == "96000003"
    assert body["eligibility"] is not None

    child = db_session.get(ChildMaster, body["child_id"])
    assert child is not None
    # The acting HR user, not the target employee whose child this is.
    assert child.CreatedBy == "96000004"


def test_hr_add_child_for_unknown_employee_returns_404(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=960005, employee_id="96000005", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000005")

    response = client.post(
        "/api/v1/hr/children",
        json={
            "employee_id": "NO-SUCH-EMPLOYEE",
            "child_name": "Aarav",
            "child_dob": "2023-01-01",
        },
    )
    assert response.status_code == 404


def test_hr_add_child_fails_when_target_employee_missing_join_date(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=960006, employee_id="96000006", Joindate=None)

    client = login_as(memp_id=960007, employee_id="96000007", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000007")

    response = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000006", "child_name": "Aarav", "child_dob": "2023-01-01"},
    )
    assert response.status_code == 400
    assert "join date" in response.json()["message"].lower()


def test_hr_add_child_respects_two_child_cap(login_as, make_employee, make_hr_approver) -> None:
    make_employee(memp_id=960008, employee_id="96000008", Joindate=datetime(2018, 1, 1))

    client = login_as(memp_id=960009, employee_id="96000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000009")

    first = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000008", "child_name": "Child One", "child_dob": "2020-01-01"},
    )
    second = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000008", "child_name": "Child Two", "child_dob": "2021-01-01"},
    )
    third = client.post(
        "/api/v1/hr/children",
        json={"employee_id": "96000008", "child_name": "Child Three", "child_dob": "2022-01-01"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 400
    assert "maximum" in third.json()["message"].lower()


def test_hr_add_child_rejects_exact_duplicate_name_and_dob(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=960010, employee_id="96000010", Joindate=datetime(2018, 1, 1))

    client = login_as(memp_id=960011, employee_id="96000011", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96000011")

    payload = {"employee_id": "96000010", "child_name": "Aarav", "child_dob": "2023-01-01"}
    first = client.post("/api/v1/hr/children", json=payload)
    second = client.post("/api/v1/hr/children", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
