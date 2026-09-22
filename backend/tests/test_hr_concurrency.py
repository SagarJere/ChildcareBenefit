"""Regression test for DECISIONS_LOG.md item 55: two concurrent requests
approving the same claim must not both succeed.

This needs two genuinely independent SQL Server connections/transactions
to exercise real row-level locking, which the shared, single-connection
`db_session` fixture every other test uses cannot do (everything funnels
through one transaction there, so a `with_for_update()` lock can never
actually block anything). So this test talks to the database directly,
commits for real, and cleans up explicitly afterward — the same pattern
`test_claims.py`'s real-MinIO test uses for state outside the normal
rolled-back transaction.
"""
import threading
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.errors import ClaimNotReviewableError
from app.models.child import ChildMaster
from app.models.claim import ClaimMaster
from app.models.claim_approval_history import ClaimApprovalHistory
from app.models.eligibility import EligibilityMaster
from app.models.employee import MasterEmpBasicInfo
from app.models.payout import PayoutAllocation, PayoutMonthlyLedger
from app.schemas.claim import ClaimCreateRequest
from app.schemas.employee import EmployeeProfile
from app.schemas.hr import ApproveRequest
from app.services import child_service, claim_service, hr_service


def test_concurrent_approve_processes_the_claim_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.database.session import get_engine

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.sqlalchemy_database_uri:
        pytest.skip("SQL Server is not configured (see backend/.env.example).")

    engine = get_engine()
    memp_id = 993_001
    employee_id = "99300001"

    setup_session = Session(bind=engine)
    try:
        setup_session.add(
            MasterEmpBasicInfo(
                MEmpID=memp_id,
                EmployeeID=employee_id,
                FullName="Concurrency Test",
                MySingleID="MSID-9930",
                Joindate=datetime(2018, 1, 1),
                IsActive=True,
            )
        )
        setup_session.flush()

        employee = EmployeeProfile(
            memp_id=memp_id,
            employee_id=employee_id,
            full_name="Concurrency Test",
            my_single_id="MSID-9930",
            join_date=datetime(2018, 1, 1),
        )
        child = child_service.add_child(
            setup_session, employee, "Kid Concurrency", date(2023, 6, 1)
        )
        claim = claim_service.create_claim(
            setup_session,
            employee,
            ClaimCreateRequest(
                child_id=child.child_id,
                invoice_date=date.today(),
                invoice_number="INV-CONCURRENCY-1",
                invoice_amount=Decimal("1000.00"),
            ),
        )
        claim_service.submit_claim(setup_session, employee, claim.claim_id)
        setup_session.commit()
        claim_id = claim.claim_id

        # Pauses thread A immediately after its claim lookup (locked or
        # not, depending on the code under test) returns, and before it
        # does anything else — in particular, before it reaches the
        # separate, pre-existing eligibility-balance lock (item 44), which
        # would otherwise also serialize thread B and make this test unable
        # to isolate whether it's *this* fix doing the blocking. This is
        # exactly the read-then-write gap the real race exploited: two
        # requests both read ClaimStatus == Submitted before either writes.
        lock_acquired = threading.Event()
        allowed_to_proceed = threading.Event()

        import app.repositories.claim_repository as claim_repository_module

        real_get_claim_by_id = claim_repository_module.get_claim_by_id
        real_get_claim_by_id_for_update = claim_repository_module.get_claim_by_id_for_update

        def _pausing_get_claim_by_id(db: Session, claim_id: int):
            result = real_get_claim_by_id(db, claim_id)
            lock_acquired.set()
            allowed_to_proceed.wait(timeout=5)
            return result

        def _pausing_get_claim_by_id_for_update(db: Session, claim_id: int):
            result = real_get_claim_by_id_for_update(db, claim_id)
            lock_acquired.set()
            allowed_to_proceed.wait(timeout=5)
            return result

        monkeypatch.setattr(claim_repository_module, "get_claim_by_id", _pausing_get_claim_by_id)
        monkeypatch.setattr(
            claim_repository_module,
            "get_claim_by_id_for_update",
            _pausing_get_claim_by_id_for_update,
        )

        results: dict[str, object] = {}

        def _run_a() -> None:
            session_a = Session(bind=engine)
            try:
                hr_service.approve_claim(
                    session_a,
                    "HR-TEST",
                    claim_id,
                    ApproveRequest(approved_amount=Decimal("1000.00"), remarks=None),
                )
                session_a.commit()
                results["a"] = "ok"
            except Exception as exc:  # noqa: BLE001
                session_a.rollback()
                results["a"] = exc
            finally:
                session_a.close()

        def _run_b() -> None:
            session_b = Session(bind=engine)
            try:
                hr_service.approve_claim(
                    session_b,
                    "HR-TEST",
                    claim_id,
                    ApproveRequest(approved_amount=Decimal("1000.00"), remarks=None),
                )
                session_b.commit()
                results["b"] = "ok"
            except Exception as exc:  # noqa: BLE001
                session_b.rollback()
                results["b"] = exc
            finally:
                session_b.close()

        thread_a = threading.Thread(target=_run_a)
        thread_b = threading.Thread(target=_run_b)

        thread_a.start()
        assert lock_acquired.wait(timeout=5), "Thread A never reached its paused checkpoint."

        thread_b.start()
        # Give B's own row-lock request a moment to actually reach the
        # database and start blocking behind A's held (uncommitted) lock.
        thread_b.join(timeout=0.5)
        assert thread_b.is_alive(), (
            "Thread B finished immediately instead of blocking on the "
            "claim's row lock — the concurrency guard isn't in effect."
        )

        allowed_to_proceed.set()
        thread_a.join(timeout=10)
        thread_b.join(timeout=10)

        assert results["a"] == "ok"
        assert isinstance(results["b"], ClaimNotReviewableError)

        verify_session = Session(bind=engine)
        try:
            approval_rows = (
                verify_session.query(ClaimApprovalHistory)
                .filter(
                    ClaimApprovalHistory.ClaimID == claim_id,
                    ClaimApprovalHistory.Action == "Approved",
                )
                .all()
            )
            assert len(approval_rows) == 1, (
                "Expected exactly one Approved history entry — the claim "
                "was processed more than once."
            )

            allocations = (
                verify_session.query(PayoutAllocation)
                .filter(PayoutAllocation.ClaimID == claim_id)
                .all()
            )
            total_allocated = sum(a.AllocatedAmount for a in allocations)
            assert total_allocated == Decimal("1000.00"), (
                f"Expected the claim's ₹1000 to be allocated exactly once, "
                f"got {total_allocated} — the payout was double-counted."
            )
        finally:
            verify_session.close()
    finally:
        cleanup_session = Session(bind=engine)
        try:
            eligibility_ids = [
                row[0]
                for row in cleanup_session.query(EligibilityMaster.EligibilityID).filter(
                    EligibilityMaster.MEmpID == memp_id
                )
            ]
            if eligibility_ids:
                cleanup_session.execute(
                    delete(PayoutAllocation).where(
                        PayoutAllocation.EligibilityID.in_(eligibility_ids)
                    )
                )
                cleanup_session.execute(
                    delete(PayoutMonthlyLedger).where(
                        PayoutMonthlyLedger.EligibilityID.in_(eligibility_ids)
                    )
                )
            claim_ids = [
                row[0]
                for row in cleanup_session.query(ClaimMaster.ClaimID).filter(
                    ClaimMaster.MEmpID == memp_id
                )
            ]
            if claim_ids:
                cleanup_session.execute(
                    delete(ClaimApprovalHistory).where(
                        ClaimApprovalHistory.ClaimID.in_(claim_ids)
                    )
                )
                cleanup_session.execute(
                    delete(ClaimMaster).where(ClaimMaster.ClaimID.in_(claim_ids))
                )
            cleanup_session.execute(
                delete(EligibilityMaster).where(EligibilityMaster.MEmpID == memp_id)
            )
            cleanup_session.execute(delete(ChildMaster).where(ChildMaster.MEmpID == memp_id))
            cleanup_session.execute(
                delete(MasterEmpBasicInfo).where(MasterEmpBasicInfo.MEmpID == memp_id)
            )
            cleanup_session.commit()
        finally:
            cleanup_session.close()
