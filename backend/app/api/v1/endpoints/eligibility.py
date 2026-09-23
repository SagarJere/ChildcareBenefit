from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.v1.csv_response import csv_response
from app.database.session import get_db
from app.dependencies.auth import get_current_employee
from app.repositories import eligibility_repository, payout_repository
from app.schemas.eligibility import (
    EligibilityResponse,
    EmployeeEligibilityReportResponse,
)
from app.schemas.employee import EmployeeProfile
from app.schemas.payout import MonthlyLedgerEntryResponse
from app.schemas.reports import PayoutReportResponse
from app.services import report_service

router = APIRouter()


@router.get("/eligibility", response_model=list[EligibilityResponse])
def list_eligibility(
    financial_year: str | None = Query(default=None, alias="financialYear"),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[EligibilityResponse]:
    rows = eligibility_repository.get_for_employee(db, current_employee.memp_id, financial_year)
    return [EligibilityResponse.from_orm_model(row) for row in rows]


@router.get("/eligibility/report", response_model=EmployeeEligibilityReportResponse)
def get_employee_eligibility_report(
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeEligibilityReportResponse:
    """Kid-wise, financial-year-wise eligibility report for the
    authenticated employee's own children — must be declared before
    `/eligibility/{child_id}` so "report" isn't matched as a child ID."""
    return report_service.build_employee_eligibility_report(db, memp_id=current_employee.memp_id)


@router.get("/eligibility/payout-report", response_model=None)
def get_employee_payout_report(
    financial_year: str | None = None,
    child_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> PayoutReportResponse | PlainTextResponse:
    """The employee-facing equivalent of HR's payout report (`GET
    /hr/reports/payout`) — claim-driven payout only (months 14+); see the
    sibling `/eligibility/payout-report/first-year` for the child's
    first-13-months auto-paid amounts. Reuses the exact same
    `report_service.build_payout_report`, just always scoped to the
    caller's own EmployeeID rather than exposing an employee filter. Must
    be declared before `/eligibility/{child_id}` so "payout-report" isn't
    matched as a child ID."""
    report = report_service.build_payout_report(
        db,
        financial_year=financial_year,
        employee_id=current_employee.employee_id,
        child_id=child_id,
        source="claim",
    )
    if format == "csv":
        return csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "my-payout.csv",
        )
    return report


@router.get("/eligibility/payout-report/first-year", response_model=None)
def get_employee_first_year_payout_report(
    financial_year: str | None = None,
    child_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> PayoutReportResponse | PlainTextResponse:
    """The employee-facing equivalent of HR's first-year payout report —
    the child's first-13-months auto-paid amounts only, with no claim
    involved. Must be declared before `/eligibility/{child_id}` for the
    same reason as the sibling route above."""
    report = report_service.build_payout_report(
        db,
        financial_year=financial_year,
        employee_id=current_employee.employee_id,
        child_id=child_id,
        source="first_year",
    )
    if format == "csv":
        return csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "my-first-year-payout.csv",
        )
    return report


@router.get("/eligibility/{child_id}", response_model=list[EligibilityResponse])
def get_eligibility_for_child(
    child_id: str,
    financial_year: str | None = Query(default=None, alias="financialYear"),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[EligibilityResponse]:
    rows = eligibility_repository.get_for_child(
        db, current_employee.memp_id, child_id, financial_year
    )
    return [EligibilityResponse.from_orm_model(row) for row in rows]


@router.get(
    "/eligibility/{child_id}/payout-schedule", response_model=list[MonthlyLedgerEntryResponse]
)
def get_payout_schedule_for_child(
    child_id: str,
    financial_year: str = Query(alias="financialYear"),
    current_employee: EmployeeProfile = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[MonthlyLedgerEntryResponse]:
    """The full month-by-month payout ledger (entitlement, carry-forward,
    allocated, closing balance) for one of the employee's own children in
    one financial year — PAYOUT_REQUIREMENTS.md §16's "payout schedule",
    at the child+FY level rather than scoped to a single claim (compare
    ClaimResponse.payout_schedule, which is per-claim)."""
    rows = eligibility_repository.get_for_child(
        db, current_employee.memp_id, child_id, financial_year
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No eligibility record exists for this child in financial year "
                f"{financial_year}."
            ),
        )
    ledger = payout_repository.get_ledger_for_eligibility(db, rows[0].EligibilityID)
    return [MonthlyLedgerEntryResponse.from_orm_model(row) for row in ledger]
