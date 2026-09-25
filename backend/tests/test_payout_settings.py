"""HR-configurable global claim-processing settings.

Covers two separate features, both user direction 2026-09-25:

- The original payout-cutoff-day/claims-blocked settings table and API
  (Increment 1 of that feature). The submission-cutoff-day's effect on
  payout month allocation is a separate increment (payout_calculator.py),
  not covered here.
- The financial-year gate (Increment 1 of the follow-up feature, same
  day): claims can only be raised for a financial year at or before
  whichever one HR has most recently opened via open_next_financial_year
  — deliberately with no automatic "current calendar FY" fallback (see
  payout_settings_service.is_financial_year_open's own comment), so this
  really can block *today's* real FY if HR hasn't gotten to opening it
  yet. The same-month-payout override's effect on the payout calculation
  is that feature's own later increment, not covered here either.

Childcare_PayoutSettings is a genuine single-row, application-wide
singleton — unlike almost everything else this test suite touches, it is
NOT scoped to any one test's data. conftest.py's client_with_db fixture
resets it to safe defaults (cutoff day 5, unblocked, no FY explicitly
opened yet — get_settings() bootstraps that to today's real FY on first
read, same-month override off) at the start of every test specifically
so a real change (e.g. from someone manually testing the HR Settings
page) can never leak in and break these tests — see that fixture's own
comment. Every test below can therefore assume that starting state.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""

from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.repositories import financial_year_repository, payout_settings_repository
from app.services import eligibility_calculator


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


def _create_claim_payload(child_id: str, invoice_number: str) -> dict:
    return {
        "child_id": child_id,
        "invoice_date": "2026-08-01",
        "institution_name": "Test Institution",
        "from_date": "2026-08-01",
        "to_date": "2026-08-01",
        "invoice_number": invoice_number,
        "invoice_amount": "1000.00",
    }


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def test_get_payout_settings_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get("/api/v1/payout-settings")
    assert response.status_code == 401


def test_get_payout_settings_defaults(login_as) -> None:
    client = login_as(memp_id=950001, employee_id="95000001", Joindate=datetime(2018, 1, 1))
    response = client.get("/api/v1/payout-settings")
    assert response.status_code == 200
    body = response.json()
    assert body["submission_cutoff_day"] == 5
    assert body["claims_blocked"] is False


def test_update_payout_settings_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 10,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert response.status_code == 401


def test_update_payout_settings_rejects_non_hr_employee(login_as) -> None:
    client = login_as(memp_id=950002, employee_id="95000002", Joindate=datetime(2018, 1, 1))
    response = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 10,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert response.status_code == 403


def test_hr_can_update_payout_settings(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950003, employee_id="95000003", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000003")

    response = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 10,
            "claims_blocked": True,
            "force_same_month_payout": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submission_cutoff_day"] == 10
    assert body["claims_blocked"] is True
    assert body["updated_by"] == "95000003"
    assert body["updated_date"] is not None

    # The update is really persisted, not just echoed back.
    refetched = client.get("/api/v1/payout-settings")
    assert refetched.json()["submission_cutoff_day"] == 10
    assert refetched.json()["claims_blocked"] is True


def test_updated_date_changes_on_every_real_change(login_as, make_hr_approver) -> None:
    """The bug report this guards against: the modified timestamp must
    move forward on a second, different change, not stay frozen."""
    client = login_as(memp_id=950011, employee_id="95000011", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000011")

    first = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 6,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert first.status_code == 200
    first_updated_date = first.json()["updated_date"]

    second = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 7,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert second.status_code == 200
    second_updated_date = second.json()["updated_date"]

    assert second_updated_date != first_updated_date
    assert second_updated_date > first_updated_date


def test_update_payout_settings_rejects_out_of_range_cutoff_day(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950004, employee_id="95000004", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000004")

    too_low = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 0,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert too_low.status_code == 422

    too_high = client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 29,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    assert too_high.status_code == 422


def test_claims_blocked_prevents_new_claim_creation(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950005, employee_id="95000005", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Settings One", "2024-06-01")
    make_hr_approver("95000005")
    client.put(
        "/api/v1/hr/payout-settings",
        json={"submission_cutoff_day": 5, "claims_blocked": True, "force_same_month_payout": False},
    )

    response = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-BLOCKED-1")
    )
    assert response.status_code == 403
    assert "paused" in response.json()["message"].lower()


def test_claims_blocked_prevents_submitting_an_existing_draft(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950006, employee_id="95000006", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Settings Two", "2024-06-01")
    claim = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-BLOCKED-2")
    ).json()

    make_hr_approver("95000006")
    client.put(
        "/api/v1/hr/payout-settings",
        json={"submission_cutoff_day": 5, "claims_blocked": True, "force_same_month_payout": False},
    )

    response = client.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert response.status_code == 403


def test_claims_blocked_does_not_prevent_editing_an_existing_draft(
    login_as, make_hr_approver
) -> None:
    """Editing a Draft (as opposed to creating or submitting one) is
    deliberately unaffected by the block."""
    client = login_as(memp_id=950007, employee_id="95000007", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Settings Three", "2024-06-01")
    claim = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-BLOCKED-3")
    ).json()

    make_hr_approver("95000007")
    client.put(
        "/api/v1/hr/payout-settings",
        json={"submission_cutoff_day": 5, "claims_blocked": True, "force_same_month_payout": False},
    )

    response = client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-BLOCKED-3",
            "invoice_amount": "1500.00",
        },
    )
    assert response.status_code == 200
    assert float(response.json()["invoice_amount"]) == 1500.00


def test_payout_settings_history_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get("/api/v1/hr/payout-settings/history")
    assert response.status_code == 401


def test_payout_settings_history_requires_hr(login_as) -> None:
    client = login_as(memp_id=950013, employee_id="95000013", Joindate=datetime(2018, 1, 1))
    response = client.get("/api/v1/hr/payout-settings/history")
    assert response.status_code == 403


def test_payout_settings_history_records_actual_changes(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950014, employee_id="95000014", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000014")

    client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 12,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 12,
            "claims_blocked": True,
            "force_same_month_payout": False,
        },
    )

    history = client.get("/api/v1/hr/payout-settings/history")
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) >= 2

    most_recent, second_most_recent = rows[0], rows[1]
    assert most_recent["changed_by"] == "95000014"
    assert most_recent["previous_submission_cutoff_day"] == 12
    assert most_recent["new_submission_cutoff_day"] == 12
    assert most_recent["previous_claims_blocked"] is False
    assert most_recent["new_claims_blocked"] is True

    # conftest's reset (day 5, unblocked) is the state before this
    # test's own first PUT, so this is deterministic even though the
    # history table itself accumulates real rows across all runs.
    assert second_most_recent["previous_submission_cutoff_day"] == 5
    assert second_most_recent["new_submission_cutoff_day"] == 12


def test_payout_settings_history_skips_a_no_op_save(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=950015, employee_id="95000015", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000015")

    client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 9,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    before = len(client.get("/api/v1/hr/payout-settings/history").json())

    # Identical values — nothing actually changed.
    client.put(
        "/api/v1/hr/payout-settings",
        json={
            "submission_cutoff_day": 9,
            "claims_blocked": False,
            "force_same_month_payout": False,
        },
    )
    after = len(client.get("/api/v1/hr/payout-settings/history").json())

    assert after == before


def test_claims_blocked_does_not_prevent_hr_review_actions(
    login_as, make_employee, make_hr_approver
) -> None:
    """HR's own approve/reject/send-back must keep working while claims
    are blocked — the block only stops new claims entering the pipeline
    (user direction 2026-09-25)."""
    claimant = login_as(memp_id=950008, employee_id="95000008", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid Settings Four", "2024-06-01")
    claim = claimant.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-BLOCKED-4")
    ).json()
    claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    make_employee(memp_id=950009, employee_id="95000009", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000009")
    _login_as_existing(claimant, "95000009")

    claimant.put(
        "/api/v1/hr/payout-settings",
        json={"submission_cutoff_day": 5, "claims_blocked": True, "force_same_month_payout": False},
    )

    approve = claimant.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve", json={"approved_amount": "1000.00"}
    )
    assert approve.status_code == 200
    assert approve.json()["claim_status"] == "Approved"


def test_open_next_financial_year_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.post("/api/v1/hr/payout-settings/open-next-financial-year")
    assert response.status_code == 401


def test_open_next_financial_year_requires_hr(login_as) -> None:
    client = login_as(memp_id=950016, employee_id="95000016", Joindate=datetime(2018, 1, 1))
    response = client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    assert response.status_code == 403


def test_open_next_financial_year_advances_by_exactly_one_each_call(
    login_as, make_hr_approver
) -> None:
    """Confirmed with the user 2026-09-25: "next" is always relative to
    whatever is currently open (bootstrapped to today's real FY on
    first read), not recomputed from today on every call — so two
    calls in a row land two years past the bootstrap value, not stuck
    at "today + 1". There is deliberately no idempotent "already there,
    no-op" case."""
    client = login_as(memp_id=950017, employee_id="95000017", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000017")

    bootstrap_fy = eligibility_calculator.compute_financial_year(date.today())
    expected_after_first = eligibility_calculator.next_financial_year_window(bootstrap_fy)
    expected_after_second = eligibility_calculator.next_financial_year_window(
        expected_after_first
    )

    first = client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    assert first.status_code == 200
    assert first.json()["open_financial_year"] == expected_after_first.label

    second = client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    assert second.status_code == 200
    assert second.json()["open_financial_year"] == expected_after_second.label


def test_open_next_financial_year_records_a_history_row_every_call(
    login_as, make_hr_approver
) -> None:
    client = login_as(memp_id=950018, employee_id="95000018", Joindate=datetime(2018, 1, 1))
    make_hr_approver("95000018")

    before = len(client.get("/api/v1/hr/payout-settings/history").json())
    client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    after_first = len(client.get("/api/v1/hr/payout-settings/history").json())
    assert after_first == before + 1

    client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    after_second = len(client.get("/api/v1/hr/payout-settings/history").json())
    assert after_second == after_first + 1

    history = client.get("/api/v1/hr/payout-settings/history").json()
    most_recent, second_most_recent = history[0], history[1]
    bootstrap_fy = eligibility_calculator.compute_financial_year(date.today())
    expected_after_first = eligibility_calculator.next_financial_year_window(bootstrap_fy)
    expected_after_second = eligibility_calculator.next_financial_year_window(
        expected_after_first
    )

    assert second_most_recent["previous_open_financial_year"] == bootstrap_fy.label
    assert second_most_recent["new_open_financial_year"] == expected_after_first.label
    assert most_recent["previous_open_financial_year"] == expected_after_first.label
    assert most_recent["new_open_financial_year"] == expected_after_second.label
    assert most_recent["changed_by"] == "95000018"
    # Unrelated fields are unchanged (conftest's reset baseline).
    assert most_recent["previous_submission_cutoff_day"] == 5
    assert most_recent["new_submission_cutoff_day"] == 5


def test_freshly_bootstrapped_settings_allow_claims_for_the_current_financial_year(
    login_as,
) -> None:
    """The very first time Childcare_PayoutSettings is ever read (here,
    via conftest's reset leaving OpenFinancialYearID NULL), it's
    bootstrapped to today's real FY — see payout_settings_repository.
    get_settings — purely so this feature doesn't block every claim in
    the app on day one. This is a one-time bootstrap, not an ongoing
    guarantee: see the next test for what happens once time has passed
    without HR acting."""
    client = login_as(memp_id=950019, employee_id="95000019", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid FY One", "2024-06-01")
    response = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-FY-CURRENT")
    )
    assert response.status_code == 201, response.text


def test_claim_is_blocked_when_hr_has_not_opened_the_current_financial_year(
    login_as, make_hr_approver, db_session: Session
) -> None:
    """The real failure mode this feature protects against, and the
    exact scenario the user asked for 2026-09-25: claim submission
    blocks entirely for a financial year — even the real, current one —
    until HR has explicitly opened it. Simulated by rolling the open FY
    back to the year before today's real one (there is no way to
    produce a literally-future invoice date through the API:
    ClaimCreateRequest already rejects those on its own, regardless of
    this feature)."""
    client = login_as(memp_id=950020, employee_id="95000020", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid FY Two", "2024-06-01")

    current_fy = eligibility_calculator.compute_financial_year(date.today())
    an_older_fy = eligibility_calculator.compute_financial_year(
        date(current_fy.start_date.year - 1, 4, 1)
    )
    settings = payout_settings_repository.get_settings(db_session)
    older_fy_row = financial_year_repository.get_or_create(db_session, an_older_fy)
    settings.OpenFinancialYearID = older_fy_row.FinancialYearID
    settings.OpenFinancialYear = older_fy_row.FinancialYear
    db_session.flush()

    blocked = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-FY-BEHIND")
    )
    assert blocked.status_code == 403
    assert current_fy.label in blocked.json()["message"]

    make_hr_approver("95000020")
    opened = client.post("/api/v1/hr/payout-settings/open-next-financial-year")
    assert opened.status_code == 200
    assert opened.json()["open_financial_year"] == current_fy.label

    allowed = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-FY-BEHIND")
    )
    assert allowed.status_code == 201, allowed.text


def test_editing_a_draft_is_also_blocked_when_its_financial_year_is_not_open(
    login_as, db_session: Session
) -> None:
    """update_claim shares _resolve_eligibility_for_invoice with
    create_claim, so it's blocked the same way if the claim's own FY
    isn't open — even for an already-existing Draft, and even without
    changing the invoice date at all — otherwise the gate could be
    bypassed just by not touching a Draft created before it closed."""
    client = login_as(memp_id=950021, employee_id="95000021", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid FY Three", "2024-06-01")
    claim = client.post(
        "/api/v1/claims", json=_create_claim_payload(child["child_id"], "INV-FY-EDIT")
    ).json()

    current_fy = eligibility_calculator.compute_financial_year(date.today())
    an_older_fy = eligibility_calculator.compute_financial_year(
        date(current_fy.start_date.year - 1, 4, 1)
    )
    settings = payout_settings_repository.get_settings(db_session)
    older_fy_row = financial_year_repository.get_or_create(db_session, an_older_fy)
    settings.OpenFinancialYearID = older_fy_row.FinancialYearID
    settings.OpenFinancialYear = older_fy_row.FinancialYear
    db_session.flush()

    response = client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-01",
            "institution_name": "Test Institution",
            "from_date": "2026-08-01",
            "to_date": "2026-08-01",
            "invoice_number": "INV-FY-EDIT",
            "invoice_amount": "1500.00",
        },
    )
    assert response.status_code == 403
    assert current_fy.label in response.json()["message"]
