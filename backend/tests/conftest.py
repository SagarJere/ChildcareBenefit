import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:5173")


@pytest.fixture()
def client() -> TestClient:
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    """A SQL Server session bound to a transaction that is always rolled
    back, so integration tests can freely read/write real tables (notably
    `Master_Emp_BasicInfo`) without leaving any trace.

    Skipped when no SQL Server connection is configured for this
    environment (see backend/.env), rather than falling back to a mock or
    in-memory database — this project's testing strategy calls for real
    SQL Server integration tests, not a substitute.
    """
    from app.core.config import get_settings
    from app.database.session import get_engine

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.sqlalchemy_database_uri:
        pytest.skip("SQL Server is not configured (see backend/.env.example).")

    engine = get_engine()
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)

    # The app's own get_db() dependency calls session.commit() on success.
    # Re-opening a SAVEPOINT after each such commit keeps the *outer*
    # transaction (and therefore everything the test does) uncommitted.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client_with_db(db_session: Session) -> TestClient:
    from app.core.config import get_settings
    from app.database.session import get_db
    from app.main import create_app
    from app.repositories import payout_settings_repository

    get_settings.cache_clear()
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Childcare_PayoutSettings is a genuine application-wide singleton,
    # not scoped to any one test's data — a rolled-back test transaction
    # still sees already-committed rows from other connections (e.g. a
    # developer manually toggling "Pause all claims" via the real HR
    # Settings page), which would otherwise silently 403 every claim-
    # creating test in the whole suite. Reset to safe defaults here,
    # within this test's own transaction, so a real-world change can
    # never again break the test suite (see DECISIONS_LOG.md's
    # payout-settings follow-up, 2026-09-25) — any test that specifically
    # cares about a different cutoff day or a blocked state still sets
    # that explicitly itself.
    settings = payout_settings_repository.get_settings(db_session)
    settings.SubmissionCutoffDay = 5
    settings.ClaimsBlocked = False
    # Same singleton-leak guard, extended for the financial-year gate and
    # same-month-payout override added 2026-09-25 (same day) — a real HR
    # "open next FY" click, or the override being left on, would
    # otherwise leak in exactly like SubmissionCutoffDay/ClaimsBlocked
    # used to.
    settings.OpenFinancialYearID = None
    settings.OpenFinancialYear = None
    settings.ForceSameMonthPayout = False
    db_session.flush()

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def jwt_secret(monkeypatch: pytest.MonkeyPatch):
    """A JWT secret for the duration of one test, regardless of what (if
    anything) is in a developer's local backend/.env."""
    from app.core.config import get_settings

    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def make_employee(db_session: Session):
    """Factory fixture: insert a Master_Emp_BasicInfo row for this test's
    transaction (rolled back afterwards, per db_session)."""
    from datetime import datetime

    from app.models.employee import MasterEmpBasicInfo

    def _make(memp_id: int, employee_id: str, **overrides: object) -> MasterEmpBasicInfo:
        defaults: dict[str, object] = {
            "FullName": "Test Employee",
            "MySingleID": "MSID-0001",
            "Joindate": datetime(2018, 1, 1),
            "IsActive": True,
        }
        defaults.update(overrides)
        employee = MasterEmpBasicInfo(MEmpID=memp_id, EmployeeID=employee_id, **defaults)
        db_session.add(employee)
        db_session.flush()
        return employee

    return _make


@pytest.fixture()
def make_hr_approver(db_session: Session):
    """Factory fixture: grant an EmployeeID HR-approver access for this
    test's transaction (rolled back afterwards, per db_session)."""
    from app.models.hr_approver import HRApprover

    def _make(employee_id: str, *, is_active: bool = True) -> HRApprover:
        approver = HRApprover(EmployeeID=employee_id, IsActive=is_active)
        db_session.add(approver)
        db_session.flush()
        return approver

    return _make


@pytest.fixture()
def login_as(client_with_db: TestClient, make_employee, jwt_secret):
    """Factory fixture: create an employee and return a TestClient that
    sends its bearer token on every subsequent request."""

    def _login_as(*, memp_id: int, employee_id: str, **employee_overrides: object) -> TestClient:
        make_employee(memp_id, employee_id, **employee_overrides)
        response = client_with_db.post("/api/v1/auth/login", json={"employee_id": employee_id})
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        client_with_db.headers.update({"Authorization": f"Bearer {token}"})
        return client_with_db

    return _login_as
