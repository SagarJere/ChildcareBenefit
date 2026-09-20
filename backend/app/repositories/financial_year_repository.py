from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.financial_year import FinancialYearMaster
from app.services.eligibility_calculator import FinancialYearWindow


def get_or_create(db: Session, fy: FinancialYearWindow) -> FinancialYearMaster:
    existing = db.execute(
        select(FinancialYearMaster).where(FinancialYearMaster.FinancialYear == fy.label)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    row = FinancialYearMaster(
        FinancialYear=fy.label,
        StartDate=fy.start_date,
        EndDate=fy.end_date,
        IsActive=True,
    )
    try:
        # A SAVEPOINT, not the outer transaction: if another concurrent
        # request already created this financial year row first
        # (FinancialYear is unique), only this insert attempt should be
        # undone — not whatever else this request's transaction has
        # already done (e.g. as part of atomically adding a child).
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return db.execute(
            select(FinancialYearMaster).where(FinancialYearMaster.FinancialYear == fy.label)
        ).scalar_one()
    return row
