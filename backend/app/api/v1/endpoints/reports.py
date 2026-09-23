from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.v1.csv_response import csv_response as _csv_response
from app.database.session import get_db
from app.dependencies.auth import get_current_hr_approver
from app.repositories import financial_year_repository
from app.schemas.employee import EmployeeProfile
from app.schemas.reports import (
    ClaimsSummaryResponse,
    EligibilityUtilizationResponse,
    HeadcountResponse,
    PayoutReportResponse,
)
from app.services import report_service

router = APIRouter()


@router.get("/hr/financial-years", response_model=list[str])
def financial_years(
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> list[str]:
    """Feeds the HR reports' financial-year filter dropdown — every FY
    label that actually has data, most recent first."""
    return [fy.FinancialYear for fy in financial_year_repository.list_all(db)]


@router.get("/hr/reports/claims-summary", response_model=None)
def claims_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    employee_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> ClaimsSummaryResponse | PlainTextResponse:
    report = report_service.build_claims_summary(
        db, date_from=date_from, date_to=date_to, status=status, employee_id=employee_id
    )
    if format == "csv":
        return _csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "claims-summary.csv",
        )
    return report


@router.get("/hr/reports/eligibility-utilization", response_model=None)
def eligibility_utilization(
    financial_year: str | None = None,
    employee_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> EligibilityUtilizationResponse | PlainTextResponse:
    report = report_service.build_eligibility_utilization(
        db, financial_year=financial_year, employee_id=employee_id
    )
    if format == "csv":
        return _csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "eligibility-utilization.csv",
        )
    return report


@router.get("/hr/reports/headcount", response_model=None)
def headcount(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> HeadcountResponse | PlainTextResponse:
    report = report_service.build_headcount(db)
    if format == "csv":
        rows: list[dict] = [
            {
                "metric": "total_employees_with_children",
                "value": report.total_employees_with_children,
            },
            {"metric": "total_children", "value": report.total_children},
            {"metric": "employees_with_one_child", "value": report.employees_with_one_child},
            {
                "metric": "employees_with_two_children",
                "value": report.employees_with_two_children,
            },
            *(
                {"metric": f"financial_year:{fy.financial_year}", "value": fy.child_count}
                for fy in report.by_financial_year
            ),
            *(
                {"metric": f"age_bracket:{bracket.age_bracket}", "value": bracket.child_count}
                for bracket in report.by_age_bracket
            ),
        ]
        return _csv_response(rows, ["metric", "value"], "headcount-summary.csv")
    return report


@router.get("/hr/reports/payout", response_model=None)
def payout_report(
    financial_year: str | None = None,
    employee_id: str | None = None,
    child_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> PayoutReportResponse | PlainTextResponse:
    """Claim-driven payout only (months 14+) — see the sibling
    `/hr/reports/payout/first-year` for the child's first-13-months
    auto-paid amounts (DECISIONS_LOG.md's first-year-payout Increment 4)."""
    report = report_service.build_payout_report(
        db,
        financial_year=financial_year,
        employee_id=employee_id,
        child_id=child_id,
        source="claim",
    )
    if format == "csv":
        return _csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "payout-report.csv",
        )
    return report


@router.get("/hr/reports/payout/first-year", response_model=None)
def first_year_payout_report(
    financial_year: str | None = None,
    employee_id: str | None = None,
    child_id: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_hr_employee: EmployeeProfile = Depends(get_current_hr_approver),
    db: Session = Depends(get_db),
) -> PayoutReportResponse | PlainTextResponse:
    """The child's first-13-months auto-paid amounts only, with no claim
    involved — see the sibling `/hr/reports/payout` for claim-driven
    payout (months 14+)."""
    report = report_service.build_payout_report(
        db,
        financial_year=financial_year,
        employee_id=employee_id,
        child_id=child_id,
        source="first_year",
    )
    if format == "csv":
        return _csv_response(
            [row.model_dump(mode="json") for row in report.rows],
            list(report.rows[0].model_dump().keys()) if report.rows else [],
            "first-year-payout-report.csv",
        )
    return report
