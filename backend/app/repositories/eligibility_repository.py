from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.eligibility import EligibilityMaster
from app.services.eligibility_calculator import EligibilityCalculation


def _utc_now_naive() -> datetime:
    """A naive UTC datetime, matching this table's GETUTCDATE() server
    default convention, for the DATETIME column this repository sets from
    application code."""
    return datetime.now(UTC).replace(tzinfo=None)


def create_eligibility(
    db: Session,
    *,
    memp_id: int,
    employee_id: str,
    child_id: str,
    child_name: str,
    child_dob: date,
    financial_year_id: int,
    calculation: EligibilityCalculation,
) -> EligibilityMaster:
    eligibility = EligibilityMaster(
        MEmpID=memp_id,
        EmployeeID=employee_id,
        ChildID=child_id,
        ChildName=child_name,
        ChildDOB=child_dob,
        FinancialYearID=financial_year_id,
        FinancialYear=calculation.financial_year,
        EligibilityStartDate=calculation.eligibility_start_date,
        EligibilityEndDate=calculation.eligibility_end_date,
        EligibleMonths=calculation.eligible_months,
        MonthlyBenefitAmount=calculation.monthly_benefit_amount,
        AllottedAmount=calculation.allotted_amount,
        UtilizedAmount=0,
        ApprovedAmount=0,
        InProgressAmount=0,
        RemainingAmount=calculation.allotted_amount,
        IsActive=True,
    )
    db.add(eligibility)
    db.flush()
    return eligibility


def get_for_employee(
    db: Session, memp_id: int, financial_year: str | None = None
) -> list[EligibilityMaster]:
    stmt = select(EligibilityMaster).where(EligibilityMaster.MEmpID == memp_id)
    if financial_year is not None:
        stmt = stmt.where(EligibilityMaster.FinancialYear == financial_year)
    return list(db.execute(stmt.order_by(EligibilityMaster.CreatedDate)).scalars().all())


def get_for_child(
    db: Session, memp_id: int, child_id: str, financial_year: str | None = None
) -> list[EligibilityMaster]:
    stmt = select(EligibilityMaster).where(
        EligibilityMaster.MEmpID == memp_id, EligibilityMaster.ChildID == child_id
    )
    if financial_year is not None:
        stmt = stmt.where(EligibilityMaster.FinancialYear == financial_year)
    return list(db.execute(stmt.order_by(EligibilityMaster.CreatedDate)).scalars().all())


def get_by_id(db: Session, eligibility_id: int) -> EligibilityMaster | None:
    """Unscoped lookup for HR use — see ClaimMaster.get_claim_by_id."""
    return db.execute(
        select(EligibilityMaster).where(EligibilityMaster.EligibilityID == eligibility_id)
    ).scalar_one_or_none()


def get_by_id_for_update(db: Session, eligibility_id: int) -> EligibilityMaster | None:
    """Row-locked lookup for the balance-check-then-update sequence in HR
    approval (see DECISIONS_LOG.md item 44) — guards against two
    concurrent approvals both reading the same stale RemainingAmount and
    together over-spending the child's financial-year balance."""
    return db.execute(
        select(EligibilityMaster)
        .where(EligibilityMaster.EligibilityID == eligibility_id)
        .with_for_update()
    ).scalar_one_or_none()


def update_balance(
    db: Session,
    eligibility: EligibilityMaster,
    *,
    approved_amount: Decimal,
    in_progress_amount: Decimal,
) -> EligibilityMaster:
    """Recomputes and persists the maintained balance columns. `Utilized`
    is kept equal to `Approved` — the same meaning "Utilized" already has
    in the HR and employee eligibility reports (DECISIONS_LOG.md items 32,
    41), now mirrored into this stored column instead of leaving it at its
    initial zero. `Remaining` (the "balance" HR's approved amount is
    checked against) is Allotted minus Approved — it deliberately does not
    reserve against In Progress claims, per the same convention."""
    eligibility.ApprovedAmount = approved_amount
    eligibility.UtilizedAmount = approved_amount
    eligibility.InProgressAmount = in_progress_amount
    eligibility.RemainingAmount = eligibility.AllottedAmount - approved_amount
    eligibility.UpdatedDate = _utc_now_naive()
    db.flush()
    return eligibility


def get_current_for_children(
    db: Session, memp_id: int, financial_year: str
) -> dict[str, EligibilityMaster]:
    """Latest (current-FY) eligibility row per ChildID, for embedding a
    summary in the children list without a separate call per child."""
    rows = db.execute(
        select(EligibilityMaster).where(
            EligibilityMaster.MEmpID == memp_id,
            EligibilityMaster.FinancialYear == financial_year,
        )
    ).scalars()
    return {row.ChildID: row for row in rows}
