"""Claims + document upload integration tests (Increment 4).

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py. Tests that need
an actual MinIO upload are skipped (not faked) when MinIO isn't
configured — see the `minio_required` fixture.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.claim_attachment import PAYMENT_PROOF, RECEIPT_INVOICE, ClaimAttachment


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def minio_required():
    from app.core.config import get_settings

    settings = get_settings()
    if not (settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key):
        pytest.skip("MinIO is not configured (see backend/.env.example).")


def test_create_claim_requires_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.post(
        "/api/v1/claims",
        json={
            "child_id": "00000000_1",
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-1",
            "invoice_amount": "1000.00",
        },
    )

    assert response.status_code == 401


def test_create_claim_rejects_unknown_child(login_as) -> None:
    client = login_as(memp_id=920001, employee_id="92000001", Joindate=datetime(2018, 1, 1))

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": "92000001_1",
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-1",
            "invoice_amount": "1000.00",
        },
    )

    assert response.status_code == 404


def test_create_claim_fails_without_eligibility_for_invoice_period(login_as) -> None:
    client = login_as(memp_id=920002, employee_id="92000002", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Two", "2023-06-01")

    # The child's eligibility record was created for the *current*
    # financial year; an invoice dated well outside it has none.
    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2010-01-15",
            "invoice_number": "INV-OLD",
            "invoice_amount": "1000.00",
        },
    )

    assert response.status_code == 400
    assert "eligibility" in response.json()["message"].lower()


def test_create_claim_defaults_claim_amount_to_invoice_amount(login_as) -> None:
    client = login_as(memp_id=920003, employee_id="92000003", Joindate=datetime(2018, 1, 1))
    # Old enough to be past the child's first-13-months first-year-payout
    # window (2026-09-23), since claims can't be raised within it.
    child = _add_child(client, "Kid Three", "2024-06-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-3",
            "invoice_amount": "2500.50",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["claim_status"] == "Draft"
    assert float(body["claim_amount"]) == 2500.50
    assert float(body["invoice_amount"]) == 2500.50
    assert body["attachments"] == []
    # Child born June 2024, invoice dated August 2026 -> month 27, docs
    # informational (see the dedicated month-13+ tests for that flag).
    assert body["requires_documents"] is True


def test_submit_claim_succeeds_for_month_thirteen_plus_without_documents(login_as) -> None:
    """Per user direction 2026-09-19 (DECISIONS_LOG.md item 38), the
    document-upload requirement is informational only for now — it does
    not block submission, even past month 12."""
    client = login_as(memp_id=920005, employee_id="92000005", Joindate=datetime(2018, 1, 1))
    # DOB 2023-01-01: by an invoice dated within the current FY
    # (2026-04-01 - 2027-03-31), the child is well past month 12.
    child = _add_child(client, "Kid Five", "2023-01-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-5",
            "invoice_amount": "1000.00",
        },
    ).json()
    assert claim["requires_documents"] is True

    response = client.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    assert response.status_code == 200
    assert response.json()["claim_status"] == "Submitted"


def test_submit_claim_succeeds_for_month_thirteen_plus_with_both_documents(
    login_as, db_session: Session
) -> None:
    client = login_as(memp_id=920006, employee_id="92000006", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Six", "2023-01-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-6",
            "invoice_amount": "1000.00",
        },
    ).json()

    # Simulate both required documents already being attached, without
    # exercising the real MinIO upload path (covered separately).
    for attachment_type in (RECEIPT_INVOICE, PAYMENT_PROOF):
        db_session.add(
            ClaimAttachment(
                ClaimID=claim["claim_id"],
                AttachmentType=attachment_type,
                OriginalFileName="doc.pdf",
                StoredFileName="stored-doc.pdf",
                BucketName="test-bucket",
                ObjectKey=f"claims/x/{attachment_type}.pdf",
                ContentType="application/pdf",
                FileSize=1234,
                UploadedBy="92000006",
            )
        )
    db_session.flush()

    response = client.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    assert response.status_code == 200
    assert response.json()["claim_status"] == "Submitted"


def test_create_claim_rejects_duplicate_invoice_number(login_as) -> None:
    client = login_as(memp_id=920014, employee_id="92000014", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Fourteen", "2024-06-01")
    payload = {
        "child_id": child["child_id"],
        "invoice_date": "2026-08-01",
        "invoice_number": "INV-14",
        "invoice_amount": "1000.00",
    }
    first = client.post("/api/v1/claims", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/claims", json=payload)
    assert second.status_code == 409
    assert "invoice number" in second.json()["message"].lower()


def test_update_claim_rejects_duplicate_invoice_number_from_another_claim(login_as) -> None:
    client = login_as(memp_id=920015, employee_id="92000015", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Fifteen", "2024-06-01")
    client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-15-A",
            "invoice_amount": "1000.00",
        },
    )
    second = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-02",
            "invoice_number": "INV-15-B",
            "invoice_amount": "1200.00",
        },
    ).json()

    response = client.put(
        f"/api/v1/claims/{second['claim_id']}",
        json={
            "invoice_date": "2026-08-02",
            "invoice_number": "INV-15-A",
            "invoice_amount": "1200.00",
        },
    )

    assert response.status_code == 409


def test_update_claim_keeps_its_own_invoice_number(login_as) -> None:
    """A claim being edited must not be flagged as a duplicate of itself."""
    client = login_as(memp_id=920016, employee_id="92000016", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Sixteen", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-16",
            "invoice_amount": "1000.00",
        },
    ).json()

    response = client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-16",
            "invoice_amount": "1500.00",
        },
    )

    assert response.status_code == 200
    assert float(response.json()["invoice_amount"]) == 1500.00


def test_create_claim_stores_optional_comments(login_as) -> None:
    client = login_as(memp_id=920017, employee_id="92000017", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Seventeen", "2024-06-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-17",
            "invoice_amount": "1000.00",
            "comments": "Please process urgently.",
        },
    )

    assert response.status_code == 201
    assert response.json()["comments"] == "Please process urgently."


def test_create_claim_comments_default_to_none(login_as) -> None:
    client = login_as(memp_id=920018, employee_id="92000018", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Eighteen", "2024-06-01")

    response = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-18",
            "invoice_amount": "1000.00",
        },
    )

    assert response.status_code == 201
    assert response.json()["comments"] is None


def test_employee_can_view_history_and_resubmit_a_sent_back_claim(
    login_as, make_employee, make_hr_approver
) -> None:
    """Per user direction 2026-09-19: an employee must be able to see HR's
    remarks/history on their own claim, and correct + resubmit a claim
    HR sent back."""
    claimant = login_as(memp_id=920019, employee_id="92000019", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid Nineteen", "2024-06-01")
    claim = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-19",
            "invoice_amount": "1000.00",
        },
    ).json()
    submitted = claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert submitted.status_code == 200

    make_employee(memp_id=920020, employee_id="92000020", Joindate=datetime(2018, 1, 1))
    make_hr_approver("92000020")
    hr_login = claimant.post("/api/v1/auth/login", json={"employee_id": "92000020"})
    hr_token = hr_login.json()["access_token"]
    claimant.headers.update({"Authorization": f"Bearer {hr_token}"})
    sent_back = claimant.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/send-back",
        json={"remarks": "Please attach a clearer invoice copy."},
    )
    assert sent_back.status_code == 200

    # Switch back to the employee.
    employee_login = claimant.post("/api/v1/auth/login", json={"employee_id": "92000019"})
    employee_token = employee_login.json()["access_token"]
    claimant.headers.update({"Authorization": f"Bearer {employee_token}"})

    detail = claimant.get(f"/api/v1/claims/{claim['claim_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["claim_status"] == "SentBack"
    assert len(body["approval_history"]) == 1
    assert body["approval_history"][0]["action"] == "SentBack"
    assert body["approval_history"][0]["action_by"] == "92000020"
    assert body["approval_history"][0]["action_by_name"] == "Test Employee"
    assert body["approval_history"][0]["remarks"] == "Please attach a clearer invoice copy."

    # A SentBack claim can be corrected and resubmitted.
    updated = claimant.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-19-CORRECTED",
            "invoice_amount": "1000.00",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["invoice_number"] == "INV-19-CORRECTED"

    resubmitted = claimant.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert resubmitted.status_code == 200
    assert resubmitted.json()["claim_status"] == "Submitted"


def test_update_claim_rejected_once_submitted(login_as) -> None:
    client = login_as(memp_id=920007, employee_id="92000007", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Seven", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-7",
            "invoice_amount": "1000.00",
        },
    ).json()
    client.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    response = client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-02",
            "invoice_number": "INV-7-B",
            "invoice_amount": "1200.00",
        },
    )

    assert response.status_code == 409


def test_list_claims_returns_only_own_claims(login_as, make_employee) -> None:
    client = login_as(memp_id=920008, employee_id="92000008", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Eight", "2024-06-01")
    client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-8",
            "invoice_amount": "1000.00",
        },
    )

    make_employee(memp_id=920009, employee_id="92000009", Joindate=datetime(2018, 1, 1))
    login_response = client.post("/api/v1/auth/login", json={"employee_id": "92000009"})
    client.headers.update({"Authorization": f"Bearer {login_response.json()['access_token']}"})

    listing = client.get("/api/v1/claims")
    assert listing.status_code == 200
    assert listing.json() == []


def test_upload_attachment_rejects_invalid_extension(login_as) -> None:
    client = login_as(memp_id=920010, employee_id="92000010", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Ten", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-10",
            "invoice_amount": "1000.00",
        },
    ).json()

    response = client.post(
        f"/api/v1/claims/{claim['claim_id']}/attachments",
        data={"attachment_type": RECEIPT_INVOICE},
        files={"file": ("malware.exe", b"not-a-real-file", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["message"].lower()


def test_upload_attachment_rejects_oversized_file(login_as) -> None:
    client = login_as(memp_id=920011, employee_id="92000011", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Eleven", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-11",
            "invoice_amount": "1000.00",
        },
    ).json()

    oversized_content = b"0" * (2 * 1024 * 1024)  # default limit is 1 MB
    response = client.post(
        f"/api/v1/claims/{claim['claim_id']}/attachments",
        data={"attachment_type": RECEIPT_INVOICE},
        files={"file": ("invoice.pdf", oversized_content, "application/pdf")},
    )

    assert response.status_code == 413


def test_upload_attachment_accepts_file_just_under_the_limit(
    login_as, minio_required, db_session: Session
) -> None:
    client = login_as(memp_id=920014, employee_id="92000014", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Fourteen", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-14",
            "invoice_amount": "1000.00",
        },
    ).json()

    just_under_limit_content = b"0" * (1024 * 1024 - 1)  # default limit is 1 MB
    response = client.post(
        f"/api/v1/claims/{claim['claim_id']}/attachments",
        data={"attachment_type": RECEIPT_INVOICE},
        files={"file": ("invoice.pdf", just_under_limit_content, "application/pdf")},
    )

    assert response.status_code == 201, response.text
    attachment = response.json()

    from app.services.storage.minio_client import get_minio_client

    row = db_session.get(ClaimAttachment, attachment["attachment_id"])
    if row is not None:
        get_minio_client().remove_object(row.BucketName, row.ObjectKey)


def test_upload_attachment_rejected_once_submitted(login_as) -> None:
    client = login_as(memp_id=920012, employee_id="92000012", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Twelve", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-12",
            "invoice_amount": "1000.00",
        },
    ).json()
    client.post(f"/api/v1/claims/{claim['claim_id']}/submit")

    response = client.post(
        f"/api/v1/claims/{claim['claim_id']}/attachments",
        data={"attachment_type": RECEIPT_INVOICE},
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 409


def test_upload_and_download_attachment_with_real_minio(
    login_as, minio_required, db_session: Session
) -> None:
    client = login_as(memp_id=920013, employee_id="92000013", Joindate=datetime(2018, 1, 1))
    child = _add_child(client, "Kid Thirteen", "2024-06-01")
    claim = client.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-13",
            "invoice_amount": "1000.00",
        },
    ).json()

    upload = client.post(
        f"/api/v1/claims/{claim['claim_id']}/attachments",
        data={"attachment_type": RECEIPT_INVOICE},
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert upload.status_code == 201
    attachment = upload.json()
    assert attachment["original_file_name"] == "invoice.pdf"

    try:
        listing = client.get(f"/api/v1/claims/{claim['claim_id']}/attachments")
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        download = client.get(
            f"/api/v1/claims/{claim['claim_id']}/attachments/{attachment['attachment_id']}/download",
            follow_redirects=False,
        )
        assert download.status_code == 307
        assert "Location" in download.headers
    finally:
        # The MinIO object is not part of the (rolled-back) DB transaction
        # — this test's own upload would otherwise accumulate in the
        # bucket on every run. The object key is an internal storage
        # detail not exposed via the API, so it's looked up directly.
        from app.services.storage.minio_client import get_minio_client

        row = db_session.get(ClaimAttachment, attachment["attachment_id"])
        if row is not None:
            get_minio_client().remove_object(row.BucketName, row.ObjectKey)
