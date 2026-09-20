"""HR Approval Workflow integration tests (Increment 5).

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
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


def _create_and_submit_claim(
    client: TestClient, child_id: str, invoice_date: str = "2026-08-01"
) -> dict:
    created = client.post(
        "/api/v1/claims",
        json={
            "child_id": child_id,
            "invoice_date": invoice_date,
            "invoice_number": "INV-HR-1",
            "invoice_amount": "2000.00",
        },
    )
    assert created.status_code == 201, created.text
    claim = created.json()
    submitted = client.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def test_hr_endpoints_require_authentication(client_with_db: TestClient) -> None:
    response = client_with_db.get("/api/v1/hr/claims")

    assert response.status_code == 401


def test_hr_endpoints_reject_non_hr_employee(login_as) -> None:
    client = login_as(memp_id=930001, employee_id="93000001", Joindate=datetime(2018, 1, 1))

    response = client.get("/api/v1/hr/claims")

    assert response.status_code == 403


def test_hr_endpoints_reject_inactive_hr_approver(login_as, make_hr_approver) -> None:
    client = login_as(memp_id=930002, employee_id="93000002", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000002", is_active=False)

    response = client.get("/api/v1/hr/claims")

    assert response.status_code == 403


def test_hr_can_list_and_view_submitted_claim(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(
        memp_id=930003,
        employee_id="93000003",
        FullName="Claimant Three",
        Joindate=datetime(2018, 1, 1),
    )
    child = _add_child(claimant, "Kid HR One", "2026-03-01")
    submitted_claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930004, employee_id="93000004", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000004")
    _login_as_existing(claimant, "93000004")
    hr_client = claimant

    listing = hr_client.get("/api/v1/hr/claims")
    assert listing.status_code == 200
    claim_ids = [c["claim_id"] for c in listing.json()]
    assert submitted_claim["claim_id"] in claim_ids

    detail = hr_client.get(f"/api/v1/hr/claims/{submitted_claim['claim_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["employee_id"] == "93000003"
    assert body["employee_name"] == "Claimant Three"
    assert body["child_name"] == "Kid HR One"
    assert body["eligibility"] is not None
    assert body["attachments"] == []
    assert body["approval_history"] == []


def test_hr_list_filters_by_status(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=930005, employee_id="93000005", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Two", "2026-03-01")
    submitted_claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930006, employee_id="93000006", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000006")
    _login_as_existing(claimant, "93000006")
    hr_client = claimant

    submitted_only = hr_client.get("/api/v1/hr/claims", params={"status": "Submitted"})
    assert submitted_only.status_code == 200
    assert len(submitted_only.json()) >= 1
    assert all(c["claim_status"] == "Submitted" for c in submitted_only.json())

    # get_claims_for_hr is intentionally unscoped (HR sees claims across all
    # employees), so the real shared database may already contain genuine
    # Approved claims from actual use — this only asserts that this test's
    # own Submitted claim is correctly excluded from the Approved filter,
    # not that no Approved claims exist anywhere.
    approved_only = hr_client.get("/api/v1/hr/claims", params={"status": "Approved"})
    assert approved_only.status_code == 200
    approved_ids = [c["claim_id"] for c in approved_only.json()]
    assert submitted_claim["claim_id"] not in approved_ids
    assert all(c["claim_status"] == "Approved" for c in approved_only.json())


def test_hr_list_filters_by_employee_and_child_for_claim_history(
    login_as, make_hr_approver, make_employee
) -> None:
    """Powers the claim-detail page's "claim history" popup: every claim
    for this exact employee+child, without mixing in the employee's other
    children's claims."""
    claimant = login_as(memp_id=930018, employee_id="93000018", Joindate=datetime(2018, 1, 1))
    child_a = _add_child(claimant, "Kid HR History A", "2026-03-01")
    child_b = _add_child(claimant, "Kid HR History B", "2026-04-01")
    claim_a1 = _create_and_submit_claim(claimant, child_a["child_id"], invoice_date="2026-08-01")
    claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child_a["child_id"],
            "invoice_date": "2026-08-02",
            "invoice_number": "INV-HR-2",
            "invoice_amount": "1500.00",
        },
    )
    _create_and_submit_claim(claimant, child_b["child_id"], invoice_date="2026-08-01")

    make_employee(memp_id=930019, employee_id="93000019", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000019")
    _login_as_existing(claimant, "93000019")
    hr_client = claimant

    history = hr_client.get(
        "/api/v1/hr/claims",
        params={"employee_id": "93000018", "child_id": child_a["child_id"]},
    )
    assert history.status_code == 200
    body = history.json()
    assert len(body) == 2
    assert all(c["child_id"] == child_a["child_id"] for c in body)
    claim_ids = {c["claim_id"] for c in body}
    assert claim_a1["claim_id"] in claim_ids


def test_hr_approve_claim_updates_status_and_history(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=930007, employee_id="93000007", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Three", "2026-03-01")
    claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930008, employee_id="93000008", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000008")
    _login_as_existing(claimant, "93000008")
    hr_client = claimant

    response = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve",
        json={"approved_amount": "1800.00", "remarks": "Looks good"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_status"] == "Approved"
    assert len(body["approval_history"]) == 1
    entry = body["approval_history"][0]
    assert entry["action"] == "Approved"
    assert entry["action_by"] == "93000008"
    assert entry["previous_status"] == "Submitted"
    assert entry["new_status"] == "Approved"
    assert float(entry["approved_amount"]) == 1800.00
    assert entry["remarks"] == "Looks good"


def test_hr_approve_rejects_amount_exceeding_invoice(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=930009, employee_id="93000009", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Four", "2026-03-01")
    claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930010, employee_id="93000010", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000010")
    _login_as_existing(claimant, "93000010")
    hr_client = claimant

    response = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/approve",
        json={"approved_amount": "999999.00"},
    )

    assert response.status_code == 400
    assert "exceed" in response.json()["message"].lower()


def test_hr_reject_requires_remarks(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=930011, employee_id="93000011", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Five", "2026-03-01")
    claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930012, employee_id="93000012", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000012")
    _login_as_existing(claimant, "93000012")
    hr_client = claimant

    response = hr_client.post(f"/api/v1/hr/claims/{claim['claim_id']}/reject", json={"remarks": ""})

    assert response.status_code == 422


def test_hr_reject_claim_updates_status_and_history(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=930013, employee_id="93000013", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Six", "2026-03-01")
    claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930014, employee_id="93000014", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000014")
    _login_as_existing(claimant, "93000014")
    hr_client = claimant

    response = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/reject",
        json={"remarks": "Invoice does not match records"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_status"] == "Rejected"
    assert body["approval_history"][0]["action"] == "Rejected"
    assert body["approval_history"][0]["approved_amount"] is None


def test_hr_cannot_act_on_non_submitted_claim(login_as, make_hr_approver, make_employee) -> None:
    claimant = login_as(memp_id=930015, employee_id="93000015", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Seven", "2026-03-01")
    # Draft claim — never submitted.
    draft = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-08-01",
            "invoice_number": "INV-DRAFT",
            "invoice_amount": "1000.00",
        },
    ).json()

    make_employee(memp_id=930016, employee_id="93000016", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000016")
    _login_as_existing(claimant, "93000016")
    hr_client = claimant

    response = hr_client.post(
        f"/api/v1/hr/claims/{draft['claim_id']}/approve", json={"approved_amount": "500.00"}
    )

    assert response.status_code == 409


def test_send_back_then_employee_can_resubmit(
    login_as, make_hr_approver, make_employee
) -> None:
    claimant = login_as(memp_id=930017, employee_id="93000017", Joindate=datetime(2018, 1, 1))
    child = _add_child(claimant, "Kid HR Eight", "2026-03-01")
    claim = _create_and_submit_claim(claimant, child["child_id"])

    make_employee(memp_id=930018, employee_id="93000018", Joindate=datetime(2018, 1, 1))
    make_hr_approver("93000018")
    _login_as_existing(claimant, "93000018")
    hr_client = claimant

    sent_back = hr_client.post(
        f"/api/v1/hr/claims/{claim['claim_id']}/send-back",
        json={"remarks": "Please attach the correct invoice"},
    )
    assert sent_back.status_code == 200
    assert sent_back.json()["claim_status"] == "SentBack"

    # Switch back to the claimant to correct and resubmit.
    _login_as_existing(claimant, "93000017")
    employee_client = claimant

    updated = employee_client.put(
        f"/api/v1/claims/{claim['claim_id']}",
        json={
            "invoice_date": "2026-08-02",
            "invoice_number": "INV-HR-1-CORRECTED",
            "invoice_amount": "2100.00",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["claim_status"] == "SentBack"

    resubmitted = employee_client.post(f"/api/v1/claims/{claim['claim_id']}/submit")
    assert resubmitted.status_code == 200
    assert resubmitted.json()["claim_status"] == "Submitted"


def test_hr_attachments_endpoints_and_isolation_from_ownership(
    login_as, make_hr_approver, make_employee, db_session: Session
) -> None:
    claimant = login_as(memp_id=930019, employee_id="93000019", Joindate=datetime(2018, 1, 1))
    # DOB far enough back that an invoice this FY is month 13+, requiring
    # documents, so there's something for HR to see in the detail view.
    child = _add_child(claimant, "Kid HR Nine", "2023-01-01")

    created = claimant.post(
        "/api/v1/claims",
        json={
            "child_id": child["child_id"],
            "invoice_date": "2026-06-01",
            "invoice_number": "INV-HR-9",
            "invoice_amount": "1500.00",
        },
    ).json()
    upload_responses = [
        claimant.post(
            f"/api/v1/claims/{created['claim_id']}/attachments",
            data={"attachment_type": RECEIPT_INVOICE},
            files={"file": ("invoice.pdf", b"%PDF-1.4 x", "application/pdf")},
        ),
        claimant.post(
            f"/api/v1/claims/{created['claim_id']}/attachments",
            data={"attachment_type": PAYMENT_PROOF},
            files={"file": ("proof.pdf", b"%PDF-1.4 y", "application/pdf")},
        ),
    ]
    if any(r.status_code == 503 for r in upload_responses):
        pytest.skip("MinIO is not configured (see backend/.env.example).")

    try:
        submitted = claimant.post(f"/api/v1/claims/{created['claim_id']}/submit")
        assert submitted.status_code == 200, submitted.text

        make_employee(memp_id=930020, employee_id="93000020", Joindate=datetime(2018, 1, 1))
        make_hr_approver("93000020")
        _login_as_existing(claimant, "93000020")
        hr_client = claimant

        listing = hr_client.get(f"/api/v1/hr/claims/{created['claim_id']}/attachments")
        assert listing.status_code == 200
        assert len(listing.json()) == 2

        detail = hr_client.get(f"/api/v1/hr/claims/{created['claim_id']}")
        assert detail.status_code == 200
        assert len(detail.json()["attachments"]) == 2
        assert detail.json()["requires_documents"] is True
    finally:
        # Real MinIO uploads happened above — not part of the rolled-back
        # DB transaction, so they must be cleaned up explicitly (see
        # test_claims.py's real-minio test for the same pattern).
        from app.services.storage.minio_client import get_minio_client

        client = get_minio_client()
        for attachment in db_session.query(ClaimAttachment).filter_by(
            ClaimID=created["claim_id"]
        ):
            client.remove_object(attachment.BucketName, attachment.ObjectKey)
