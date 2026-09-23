"""Data access for the payout ledger/allocation — see
PAYOUT_REQUIREMENTS.md and app/services/payout_service.py.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import APPROVED, ClaimMaster
from app.models.claim_approval_history import APPROVED as HISTORY_APPROVED
from app.models.claim_approval_history import ClaimApprovalHistory
from app.models.eligibility import EligibilityMaster
from app.models.payout import PayoutAllocation, PayoutMonthlyLedger
from app.services.payout_calculator import (
    ApprovedClaimInput,
    MonthlyLedgerEntry,
    PayoutAllocationEntry,
)


def get_approved_claims_with_approval_time(
    db: Session, eligibility_id: int
) -> list[ApprovedClaimInput]:
    """Every Approved claim for this eligibility, with the amount and
    timestamp HR actually approved it at — sourced from
    Childcare_ClaimApprovalHistory (not ClaimMaster.ClaimAmount), since
    HR may approve a different amount than what was claimed, and a claim
    is approved at most once in this application (see
    report_repository.get_approved_totals_by_eligibility)."""
    rows = db.execute(
        select(
            ClaimApprovalHistory.ClaimID,
            ClaimApprovalHistory.ApprovedAmount,
            ClaimApprovalHistory.ActionDate,
        )
        .join(ClaimMaster, ClaimMaster.ClaimID == ClaimApprovalHistory.ClaimID)
        .where(
            ClaimMaster.EligibilityID == eligibility_id,
            ClaimMaster.ClaimStatus == APPROVED,
            ClaimApprovalHistory.Action == HISTORY_APPROVED,
        )
    ).all()
    return [
        ApprovedClaimInput(
            claim_id=claim_id, approved_amount=approved_amount, approved_at=action_date
        )
        for claim_id, approved_amount, action_date in rows
    ]


def replace_ledger_and_allocations(
    db: Session,
    *,
    eligibility: EligibilityMaster,
    ledger_entries: list[MonthlyLedgerEntry],
    allocation_entries: list[PayoutAllocationEntry],
) -> None:
    """Wholesale replace: delete every existing ledger/allocation row for
    this EligibilityID, then insert freshly computed ones. Both tables are
    purely derived (PAYOUT_REQUIREMENTS.md §7/§10) — never hand-edited —
    so this is always safe."""
    db.query(PayoutAllocation).filter(
        PayoutAllocation.EligibilityID == eligibility.EligibilityID
    ).delete()
    db.query(PayoutMonthlyLedger).filter(
        PayoutMonthlyLedger.EligibilityID == eligibility.EligibilityID
    ).delete()
    db.flush()

    ledger_id_by_month = {}
    for entry in ledger_entries:
        ledger_row = PayoutMonthlyLedger(
            MEmpID=eligibility.MEmpID,
            EmployeeID=eligibility.EmployeeID,
            ChildID=eligibility.ChildID,
            EligibilityID=eligibility.EligibilityID,
            FinancialYearID=eligibility.FinancialYearID,
            FinancialYear=eligibility.FinancialYear,
            PayoutMonth=entry.month,
            EntitlementAmount=entry.entitlement_amount,
            OpeningBalance=entry.opening_balance,
            TotalAvailableAmount=entry.total_available_amount,
            FirstYearPayoutAmount=entry.first_year_payout_amount,
            ClaimAllocatedAmount=entry.claim_allocated_amount,
            AdjustmentAmount=0,
            ClosingBalance=entry.carry_forward_amount,
            CalculatedPayoutAmount=entry.first_year_payout_amount + entry.claim_allocated_amount,
        )
        db.add(ledger_row)
        db.flush()
        ledger_id_by_month[entry.month] = ledger_row.PayoutLedgerID

    for allocation in allocation_entries:
        db.add(
            PayoutAllocation(
                ClaimID=allocation.claim_id,
                PayoutLedgerID=ledger_id_by_month[allocation.month],
                MEmpID=eligibility.MEmpID,
                EmployeeID=eligibility.EmployeeID,
                ChildID=eligibility.ChildID,
                EligibilityID=eligibility.EligibilityID,
                FinancialYearID=eligibility.FinancialYearID,
                PayoutMonth=allocation.month,
                AllocationSequence=allocation.allocation_sequence,
                AllocatedAmount=allocation.allocated_amount,
            )
        )
    db.flush()


def get_allocations_for_claim(db: Session, claim_id: int) -> list[PayoutAllocation]:
    """A single claim's own payout schedule — see PAYOUT_REQUIREMENTS.md
    §16 (the employee/HR-facing "when will this be paid" view)."""
    return list(
        db.execute(
            select(PayoutAllocation)
            .where(PayoutAllocation.ClaimID == claim_id)
            .order_by(PayoutAllocation.PayoutMonth)
        )
        .scalars()
        .all()
    )


def get_ledger_rows_for_report(
    db: Session,
    *,
    financial_year: str | None = None,
    employee_id: str | None = None,
    child_id: str | None = None,
) -> list[PayoutMonthlyLedger]:
    """Unscoped (across all employees) — for the HR payout report only.
    Only children/financial-years with at least one approved claim ever
    have ledger rows at all (recompute is only triggered by an approval),
    so this naturally excludes anything with nothing to report."""
    stmt = select(PayoutMonthlyLedger)
    if financial_year is not None:
        stmt = stmt.where(PayoutMonthlyLedger.FinancialYear == financial_year)
    if employee_id is not None:
        stmt = stmt.where(PayoutMonthlyLedger.EmployeeID == employee_id)
    if child_id is not None:
        stmt = stmt.where(PayoutMonthlyLedger.ChildID == child_id)
    return list(
        db.execute(
            stmt.order_by(
                PayoutMonthlyLedger.EmployeeID,
                PayoutMonthlyLedger.ChildID,
                PayoutMonthlyLedger.FinancialYear,
                PayoutMonthlyLedger.PayoutMonth,
            )
        )
        .scalars()
        .all()
    )


def get_ledger_for_eligibility(db: Session, eligibility_id: int) -> list[PayoutMonthlyLedger]:
    return list(
        db.execute(
            select(PayoutMonthlyLedger)
            .where(PayoutMonthlyLedger.EligibilityID == eligibility_id)
            .order_by(PayoutMonthlyLedger.PayoutMonth)
        )
        .scalars()
        .all()
    )


def get_allocations_for_eligibility(db: Session, eligibility_id: int) -> list[PayoutAllocation]:
    return list(
        db.execute(
            select(PayoutAllocation)
            .where(PayoutAllocation.EligibilityID == eligibility_id)
            .order_by(PayoutAllocation.PayoutMonth, PayoutAllocation.ClaimID)
        )
        .scalars()
        .all()
    )
