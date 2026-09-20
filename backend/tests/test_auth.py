"""Employee Login integration tests.

These run against the real SQL Server configured for this environment
(see backend/.env.example), inside a transaction that is always rolled
back — see the `db_session` / `client_with_db` fixtures in conftest.py.
They are skipped, not faked, when no database is configured.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.models.employee import MasterEmpBasicInfo

pytestmark = pytest.mark.usefixtures("jwt_secret")


def test_login_rejects_blank_employee_id(client_with_db: TestClient) -> None:
    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": ""})

    assert response.status_code == 422


def test_login_returns_401_for_unknown_employee(client_with_db: TestClient) -> None:
    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": "90000099"})

    assert response.status_code == 401
    assert response.json()["message"] == "Employee ID not found or not active."


def test_login_returns_401_for_inactive_employee(
    client_with_db: TestClient, make_employee
) -> None:
    make_employee(memp_id=900001, employee_id="90000001", IsActive=False)

    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": "90000001"})

    assert response.status_code == 401


def test_login_returns_401_for_null_active_flag(
    client_with_db: TestClient, make_employee
) -> None:
    make_employee(memp_id=900002, employee_id="90000002", IsActive=None)

    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": "90000002"})

    assert response.status_code == 401


def test_active_employees_endpoint_requires_no_authentication(
    client_with_db: TestClient, make_employee
) -> None:
    """Deliberately public — feeds the login page's autocomplete before
    the user has a token. See DECISIONS_LOG.md item 42."""
    make_employee(memp_id=900010, employee_id="90000010", FullName="Kiran Shah", IsActive=True)

    response = client_with_db.get("/api/v1/auth/active-employees")

    assert response.status_code == 200
    employee_ids = {row["employee_id"] for row in response.json()}
    assert "90000010" in employee_ids


def test_active_employees_endpoint_excludes_inactive_and_null_active(
    client_with_db: TestClient, make_employee
) -> None:
    make_employee(memp_id=900011, employee_id="90000011", IsActive=False)
    make_employee(memp_id=900012, employee_id="90000012", IsActive=None)
    make_employee(memp_id=900013, employee_id="90000013", FullName="Meera Iyer", IsActive=True)

    response = client_with_db.get("/api/v1/auth/active-employees")

    assert response.status_code == 200
    employee_ids = {row["employee_id"] for row in response.json()}
    assert "90000011" not in employee_ids
    assert "90000012" not in employee_ids
    assert "90000013" in employee_ids
    row = next(r for r in response.json() if r["employee_id"] == "90000013")
    assert row["full_name"] == "Meera Iyer"


def test_login_succeeds_for_active_employee(client_with_db: TestClient, make_employee) -> None:
    make_employee(
        memp_id=900003,
        employee_id="90000003",
        FullName="Asha Rao",
        MySingleID="MSID-9003",
        Joindate=datetime(2021, 4, 15),
        IsActive=True,
    )

    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": "90000003"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body and body["access_token"]

    employee = body["employee"]
    assert employee["memp_id"] == 900003
    assert employee["employee_id"] == "90000003"
    assert employee["full_name"] == "Asha Rao"
    assert employee["my_single_id"] == "MSID-9003"
    assert "gender" not in employee

    assert employee["is_hr_approver"] is False

    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == "90000003"
    assert payload["memp_id"] == 900003


def test_login_reflects_hr_approver_status(
    client_with_db: TestClient, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=900006, employee_id="90000006")
    make_hr_approver("90000006")

    response = client_with_db.post("/api/v1/auth/login", json={"employee_id": "90000006"})

    assert response.status_code == 200
    assert response.json()["employee"]["is_hr_approver"] is True


def test_me_reflects_hr_approver_status(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=900007, employee_id="90000007")
    make_hr_approver("90000007")

    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json()["is_hr_approver"] is True


def test_me_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get("/api/v1/me")

    assert response.status_code == 401


def test_me_rejects_garbage_token(client_with_db: TestClient) -> None:
    response = client_with_db.get(
        "/api/v1/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_me_returns_profile_for_valid_token(login_as) -> None:
    client = login_as(memp_id=900004, employee_id="90000004", FullName="Kiran Shah")

    response = client.get("/api/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["memp_id"] == 900004
    assert body["employee_id"] == "90000004"
    assert body["full_name"] == "Kiran Shah"


def test_me_rejects_token_for_employee_deactivated_after_login(
    login_as, db_session: Session
) -> None:
    client = login_as(memp_id=900005, employee_id="90000005", IsActive=True)

    employee = db_session.get(MasterEmpBasicInfo, 900005)
    employee.IsActive = False
    db_session.flush()

    response = client.get("/api/v1/me")

    assert response.status_code == 401
