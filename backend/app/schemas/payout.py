"""Employee/HR-facing payout views — see PAYOUT_REQUIREMENTS.md §16.

Thin read views over Childcare_PayoutAllocation (one claim's own payout
schedule) and Childcare_PayoutMonthlyLedger (the full child+financial-year
monthly picture: entitlement, carry-forward, and what's been allocated).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.payout import PayoutAllocation, PayoutMonthlyLedger


class PayoutScheduleEntry(BaseModel):
    month: date
    allocated_amount: Decimal

    @classmethod
    def from_orm_model(cls, allocation: PayoutAllocation) -> PayoutScheduleEntry:
        return cls(month=allocation.PayoutMonth, allocated_amount=allocation.AllocatedAmount)


class MonthlyLedgerEntryResponse(BaseModel):
    month: date
    entitlement_amount: Decimal
    opening_balance: Decimal
    total_available_amount: Decimal
    first_year_payout_amount: Decimal
    claim_allocated_amount: Decimal
    adjustment_amount: Decimal
    closing_balance: Decimal
    calculated_payout_amount: Decimal

    @classmethod
    def from_orm_model(cls, ledger: PayoutMonthlyLedger) -> MonthlyLedgerEntryResponse:
        return cls(
            month=ledger.PayoutMonth,
            entitlement_amount=ledger.EntitlementAmount,
            opening_balance=ledger.OpeningBalance,
            total_available_amount=ledger.TotalAvailableAmount,
            first_year_payout_amount=ledger.FirstYearPayoutAmount,
            claim_allocated_amount=ledger.ClaimAllocatedAmount,
            adjustment_amount=ledger.AdjustmentAmount,
            closing_balance=ledger.ClosingBalance,
            calculated_payout_amount=ledger.CalculatedPayoutAmount,
        )
