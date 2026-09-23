"""Security & performance hardening tests (Increment 7).

These target the checklist in ChildcareBenefit_Codex_Documentation/
SECURITY.md directly: ownership can't be bypassed, backend authorization
can't be sidestepped, uploaded filenames can't escape their storage
prefix, tokens/access are revoked promptly, and list endpoints don't
regress into N+1 query patterns as data grows.

Run against the real SQL Server configured for this environment, inside a
transaction that is always rolled back — see conftest.py.
"""
from datetime import datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import TokenError, decode_access_token
from app.models.claim_attachment import RECEIPT_INVOICE, ClaimAttachment
from app.models.hr_approver import HRApprover


def _add_child(client: TestClient, name: str, dob: str) -> dict:
    response = client.post("/api/v1/children", json={"child_name": name, "child_dob": dob})
    assert response.status_code == 201, response.text
    return response.json()


def _login_as_existing(client: TestClient, employee_id: str) -> None:
    response = client.post("/api/v1/auth/login", json={"employee_id": employee_id})
    assert response.status_code == 200, response.text
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


class TestPathTraversalInUploadedFilenames:
    def test_uploaded_filename_cannot_escape_its_storage_prefix(
        self, login_as, db_session: Session
    ) -> None:
        client = login_as(memp_id=950001, employee_id="95000001", Joindate=datetime(2018, 1, 1))
        child = _add_child(client, "Sec Kid One", "2024-06-01")
        claim = client.post(
            "/api/v1/claims",
            json={
                "child_id": child["child_id"],
                "invoice_date": "2026-08-01",
                "invoice_number": "INV-SEC-1",
                "invoice_amount": "1000.00",
            },
        ).json()

        response = client.post(
            f"/api/v1/claims/{claim['claim_id']}/attachments",
            data={"attachment_type": RECEIPT_INVOICE},
            files={
                # An allowed extension disguising a traversal attempt —
                # the extension check alone would let this through, so
                # this specifically exercises _safe_filename's own
                # defense rather than the (separate) extension allowlist.
                "file": ("../../../../etc/passwd.pdf", b"%PDF-1.4 x", "application/pdf"),
            },
        )

        if response.status_code == 503:
            pytest.skip("MinIO is not configured (see backend/.env.example).")
        assert response.status_code == 201, response.text
        attachment_id = response.json()["attachment_id"]

        row = db_session.get(ClaimAttachment, attachment_id)
        assert row is not None
        try:
            assert ".." not in row.ObjectKey
            assert "/etc/" not in row.ObjectKey
            assert row.ObjectKey.startswith(
                f"claims/95000001/{child['child_id']}/{claim['claim_id']}/"
            )
            # The object key has exactly the five expected path segments
            # (claims/employee_id/child_id/claim_id/filename) — nothing
            # from the malicious filename introduced extra segments.
            assert row.ObjectKey.count("/") == 4
        finally:
            # This test's upload is real (MinIO, not just the rolled-back
            # DB row) — clean it up the same way as the equivalent test in
            # test_claims.py.
            from app.services.storage.minio_client import get_minio_client

            get_minio_client().remove_object(row.BucketName, row.ObjectKey)


class TestTokenExpiryAndRevocation:
    def test_expired_token_is_rejected(self, client_with_db: TestClient, jwt_secret) -> None:
        settings = get_settings()
        expired_payload = {
            "sub": "00000001",
            "memp_id": 1,
            "iat": datetime.now() - timedelta(hours=2),
            "exp": datetime.now() - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        with pytest.raises(TokenError):
            decode_access_token(expired_token)

        response = client_with_db.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_hr_access_revoked_mid_session_is_immediately_rejected(
        self, login_as, make_hr_approver, db_session: Session
    ) -> None:
        client = login_as(memp_id=950002, employee_id="95000002", Joindate=datetime(2018, 1, 1))
        make_hr_approver("95000002")

        assert client.get("/api/v1/hr/claims").status_code == 200

        approver_row = (
            db_session.query(HRApprover).filter_by(EmployeeID="95000002").one()
        )
        approver_row.IsActive = False
        db_session.flush()

        response = client.get("/api/v1/hr/claims")
        assert response.status_code == 403


class TestCrossEmployeeOwnershipIsEnforced:
    def test_employee_cannot_download_another_employees_attachment(
        self, login_as, make_employee, db_session: Session
    ) -> None:
        owner = login_as(memp_id=950003, employee_id="95000003", Joindate=datetime(2018, 1, 1))
        child = _add_child(owner, "Sec Kid Two", "2024-06-01")
        claim = owner.post(
            "/api/v1/claims",
            json={
                "child_id": child["child_id"],
                "invoice_date": "2026-08-01",
                "invoice_number": "INV-SEC-2",
                "invoice_amount": "1000.00",
            },
        ).json()
        db_session.add(
            ClaimAttachment(
                ClaimID=claim["claim_id"],
                AttachmentType=RECEIPT_INVOICE,
                OriginalFileName="invoice.pdf",
                StoredFileName="stored.pdf",
                BucketName="test-bucket",
                ObjectKey=f"claims/95000003/{child['child_id']}/{claim['claim_id']}/stored.pdf",
                ContentType="application/pdf",
                FileSize=100,
                UploadedBy="95000003",
            )
        )
        db_session.flush()
        attachment_id = (
            db_session.query(ClaimAttachment).filter_by(ClaimID=claim["claim_id"]).one()
        ).AttachmentID

        make_employee(memp_id=950004, employee_id="95000004", Joindate=datetime(2018, 1, 1))
        _login_as_existing(owner, "95000004")
        other_client = owner

        response = other_client.get(
            f"/api/v1/claims/{claim['claim_id']}/attachments/{attachment_id}/download"
        )
        assert response.status_code == 404

        listing = other_client.get(f"/api/v1/claims/{claim['claim_id']}/attachments")
        assert listing.status_code == 404

        get_claim = other_client.get(f"/api/v1/claims/{claim['claim_id']}")
        assert get_claim.status_code == 404


class TestInjectionAndCorsHardening:
    def test_sql_injection_style_filter_returns_empty_not_an_error(
        self, login_as, make_hr_approver
    ) -> None:
        client = login_as(memp_id=950005, employee_id="95000005", Joindate=datetime(2018, 1, 1))
        make_hr_approver("95000005")

        response = client.get(
            "/api/v1/hr/reports/claims-summary",
            params={"employee_id": "' OR '1'='1"},
        )

        assert response.status_code == 200
        assert response.json()["rows"] == []

    def test_disallowed_cors_origin_does_not_receive_allow_origin_header(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/api/v1/health", headers={"Origin": "http://evil.example.com"}
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"

    def test_configured_origin_does_receive_allow_origin_header(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/api/v1/health", headers={"Origin": "http://localhost:5173"}
        )

        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


class TestNPlusOneQueryRegression:
    def test_hr_claims_list_query_count_does_not_scale_with_claim_count(
        self, login_as, make_hr_approver, make_employee, db_session: Session
    ) -> None:
        claimant = login_as(
            memp_id=950006, employee_id="95000006", Joindate=datetime(2018, 1, 1)
        )
        child = _add_child(claimant, "Sec Kid Three", "2024-06-01")
        for i in range(5):
            created = claimant.post(
                "/api/v1/claims",
                json={
                    "child_id": child["child_id"],
                    "invoice_date": "2026-08-01",
                    "invoice_number": f"INV-SCALE-{i}",
                    "invoice_amount": "100.00",
                },
            )
            assert created.status_code == 201
            claimant.post(f"/api/v1/claims/{created.json()['claim_id']}/submit")

        make_employee(memp_id=950007, employee_id="95000007", Joindate=datetime(2018, 1, 1))
        make_hr_approver("95000007")
        _login_as_existing(claimant, "95000007")
        hr_client = claimant

        query_count = {"n": 0}

        def _count(*args, **kwargs):
            query_count["n"] += 1

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", _count)
        try:
            response = hr_client.get("/api/v1/hr/claims")
        finally:
            event.remove(engine, "before_cursor_execute", _count)

        assert response.status_code == 200
        assert len(response.json()) >= 5
        # Fixed number of queries regardless of how many claims are in the
        # list (auth lookups + claims + one bulk child fetch + one bulk
        # employee-name fetch) — not one extra pair of queries per claim.
        assert query_count["n"] < 10, (
            f"Expected a small constant number of queries, got {query_count['n']} "
            "for 5 claims — likely an N+1 regression."
        )
