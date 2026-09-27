"""HR bulk-add-children from a CSV file (user direction 2026-09-26) —
Increment 2 of the HR-add-child feature.

Preview and commit share the exact same per-row logic (see
child_bulk_service.py's own comment) — preview always rolls back, commit
doesn't. These tests focus on that distinction, on best-effort per-row
reporting (one bad row doesn't block the others), and on file-level
validation, since the underlying single-add rules (2-child cap,
duplicate check, eligibility) are already exhaustively covered by
test_children.py and test_hr_add_child.py.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bulk_add_children import BulkAddChildrenBatch, BulkAddChildrenRow
from app.models.child import ChildMaster


def _csv(rows: list[str]) -> bytes:
    return ("employee_id,child_name,child_dob\n" + "\n".join(rows)).encode("utf-8")


def _upload(client: TestClient, path: str, content: bytes):
    return client.post(path, files={"file": ("children.csv", content, "text/csv")})


def test_bulk_preview_requires_authentication(client_with_db: TestClient) -> None:
    response = _upload(
        client_with_db, "/api/v1/hr/children/bulk/preview", _csv(["96100001,Aarav,2023-01-01"])
    )
    assert response.status_code == 401


def test_bulk_preview_requires_hr(login_as) -> None:
    client = login_as(memp_id=961001, employee_id="96100101", Joindate=datetime(2018, 1, 1))
    response = _upload(
        client, "/api/v1/hr/children/bulk/preview", _csv(["96100101,Aarav,2023-01-01"])
    )
    assert response.status_code == 403


def test_bulk_rejects_missing_columns(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=961002, employee_id="96100102", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100102")

    bad_content = b"employee_id,child_name\n96100102,Aarav\n"
    response = _upload(client, "/api/v1/hr/children/bulk/preview", bad_content)
    assert response.status_code == 400
    assert "child_dob" in response.json()["message"]


def test_bulk_rejects_too_many_rows(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=961003, employee_id="96100103", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100103")

    rows = [f"96100103,Kid {i},2020-01-01" for i in range(201)]
    response = _upload(client, "/api/v1/hr/children/bulk/preview", _csv(rows))
    assert response.status_code == 400
    assert "exceeds the limit" in response.json()["message"]


def test_bulk_preview_reports_success_but_persists_nothing(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    make_employee(memp_id=961004, employee_id="96100104", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961005, employee_id="96100105", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100105")

    response = _upload(
        client, "/api/v1/hr/children/bulk/preview", _csv(["96100104,Aarav,2023-01-01"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["succeeded"] == 1
    assert body["results"][0]["status"] == "created"
    assert body["results"][0]["child_id"] == "96100104_1"

    # Nothing actually persisted.
    existing = (
        db_session.query(ChildMaster).filter(ChildMaster.EmployeeID == "96100104").all()
    )
    assert existing == []


def test_bulk_commit_actually_persists(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    make_employee(memp_id=961006, employee_id="96100106", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961007, employee_id="96100107", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100107")

    response = _upload(
        client, "/api/v1/hr/children/bulk/commit", _csv(["96100106,Aarav,2023-01-01"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["succeeded"] == 1
    assert body["results"][0]["status"] == "created"

    child = db_session.get(ChildMaster, body["results"][0]["child_id"])
    assert child is not None
    assert child.CreatedBy == "96100107"


def test_bulk_commit_is_best_effort_not_all_or_nothing(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    """One bad row (unknown employee) must not block the good rows in
    the same file."""
    make_employee(memp_id=961008, employee_id="96100108", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961009, employee_id="96100109", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100109")

    rows = [
        "96100108,Good Kid,2023-01-01",
        "NO-SUCH-EMPLOYEE,Bad Kid,2023-01-01",
    ]
    response = _upload(client, "/api/v1/hr/children/bulk/commit", _csv(rows))
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert body["succeeded"] == 1
    assert body["failed"] == 1

    good_result, bad_result = body["results"]
    assert good_result["status"] == "created"
    assert bad_result["status"] == "failed"
    assert bad_result["row_number"] == 3  # header is row 1

    child = db_session.get(ChildMaster, good_result["child_id"])
    assert child is not None


def test_bulk_two_child_cap_applies_cumulatively_within_the_same_file(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=961010, employee_id="96100110", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961011, employee_id="96100111", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100111")

    rows = [
        "96100110,Child One,2020-01-01",
        "96100110,Child Two,2021-01-01",
        "96100110,Child Three,2022-01-01",
    ]
    response = _upload(client, "/api/v1/hr/children/bulk/commit", _csv(rows))
    assert response.status_code == 200
    statuses = [r["status"] for r in response.json()["results"]]
    assert statuses == ["created", "created", "failed"]
    assert "maximum" in response.json()["results"][2]["message"].lower()


def test_bulk_duplicate_within_the_same_file_is_caught(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=961012, employee_id="96100112", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961013, employee_id="96100113", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100113")

    rows = [
        "96100112,Aarav,2023-01-01",
        "96100112,Aarav,2023-01-01",
    ]
    response = _upload(client, "/api/v1/hr/children/bulk/commit", _csv(rows))
    assert response.status_code == 200
    statuses = [r["status"] for r in response.json()["results"]]
    assert statuses == ["created", "failed"]


def test_bulk_row_with_invalid_date_is_reported_without_stopping_the_batch(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=961014, employee_id="96100114", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961015, employee_id="96100115", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100115")

    rows = [
        "96100114,Bad Date Kid,not-a-date",
        "96100114,Good Kid,2023-01-01",
    ]
    response = _upload(client, "/api/v1/hr/children/bulk/commit", _csv(rows))
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["status"] == "failed"
    assert "not a valid date" in results[0]["message"]


def test_bulk_accepts_dd_mm_yyyy_date_format(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    """User-reported bug 2026-09-26: Excel commonly exports/displays
    dates in day-first format for this locale (India) — '23-12-2023'
    was being rejected because only strict ISO (YYYY-MM-DD) was
    accepted. Also confirms day and month land in the right fields
    (23rd of December, not swapped) rather than just "some date"
    parsing without erroring."""
    make_employee(memp_id=961016, employee_id="96100116", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961017, employee_id="96100117", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100117")

    response = _upload(
        client, "/api/v1/hr/children/bulk/commit", _csv(["96100116,Aarav,23-12-2023"])
    )
    assert response.status_code == 200
    body = response.json()["results"][0]
    assert body["status"] == "created"
    assert body["child_dob"] == "2023-12-23"

    child = db_session.get(ChildMaster, body["child_id"])
    assert child is not None
    assert child.ChildDOB.isoformat() == "2023-12-23"


def test_bulk_commit_records_a_permanent_audit_batch(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    """User direction 2026-09-26: this is the defense against a later
    dispute ("I uploaded 2, only 1 was added") — the exact per-row
    outcome must be recorded permanently, not just returned once in the
    HTTP response."""
    make_employee(memp_id=961018, employee_id="96100118", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961019, employee_id="96100119", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100119")

    rows = [
        "96100118,Good Kid,2023-01-01",
        "96100118,Good Kid,2023-01-01",  # duplicate of the row above
    ]
    response = _upload(client, "/api/v1/hr/children/bulk/commit", _csv(rows))
    assert response.status_code == 200

    batch = (
        db_session.query(BulkAddChildrenBatch)
        .filter(BulkAddChildrenBatch.UploadedBy == "96100119")
        .one()
    )
    assert batch.UploadedFileName == "children.csv"
    assert batch.TotalRows == 2
    assert batch.SucceededCount == 1
    assert batch.FailedCount == 1

    persisted_rows = (
        db_session.query(BulkAddChildrenRow)
        .filter(BulkAddChildrenRow.BulkUploadID == batch.BulkUploadID)
        .order_by(BulkAddChildrenRow.RowNumber)
        .all()
    )
    assert len(persisted_rows) == 2
    assert persisted_rows[0].Status == "Created"
    assert persisted_rows[0].ChildID is not None
    assert persisted_rows[1].Status == "Failed"
    assert persisted_rows[1].ChildID is None
    assert "already on record" in persisted_rows[1].Message


def test_bulk_preview_does_not_create_an_audit_batch(
    login_as, make_employee, make_hr_approver, db_session: Session
) -> None:
    make_employee(memp_id=961020, employee_id="96100120", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961021, employee_id="96100121", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100121")

    response = _upload(
        client, "/api/v1/hr/children/bulk/preview", _csv(["96100120,Aarav,2023-01-01"])
    )
    assert response.status_code == 200

    count = (
        db_session.query(BulkAddChildrenBatch)
        .filter(BulkAddChildrenBatch.UploadedBy == "96100121")
        .count()
    )
    assert count == 0


def test_bulk_history_requires_hr(login_as) -> None:
    client = login_as(memp_id=961022, employee_id="96100122", Joindate=datetime(2018, 1, 1))
    response = client.get("/api/v1/hr/children/bulk/history")
    assert response.status_code == 403


def test_bulk_history_list_and_detail(
    login_as, make_employee, make_hr_approver
) -> None:
    make_employee(memp_id=961023, employee_id="96100123", Joindate=datetime(2018, 1, 1))
    client = login_as(memp_id=961024, employee_id="96100124", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100124")

    commit = _upload(
        client, "/api/v1/hr/children/bulk/commit", _csv(["96100123,Aarav,2023-01-01"])
    )
    assert commit.status_code == 200

    history = client.get("/api/v1/hr/children/bulk/history")
    assert history.status_code == 200
    batches = history.json()
    assert len(batches) >= 1
    most_recent = batches[0]
    assert most_recent["uploaded_by"] == "96100124"
    assert most_recent["uploaded_file_name"] == "children.csv"
    assert most_recent["succeeded_count"] == 1

    detail = client.get(f"/api/v1/hr/children/bulk/history/{most_recent['bulk_upload_id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["results"][0]["employee_id"] == "96100123"
    assert detail_body["results"][0]["status"] == "created"


def test_bulk_history_detail_404_for_unknown_batch(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=961025, employee_id="96100125", Joindate=datetime(2018, 1, 1))
    make_hr_approver("96100125")

    response = client.get("/api/v1/hr/children/bulk/history/999999999")
    assert response.status_code == 404
