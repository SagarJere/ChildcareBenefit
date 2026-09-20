"""Shared CSV-download helper for report endpoints (HR and employee-facing
alike) — see app/services/report_service.rows_to_csv for the actual CSV
formatting.
"""
from fastapi.responses import PlainTextResponse

from app.services import report_service


def csv_response(rows: list[dict], fieldnames: list[str], filename: str) -> PlainTextResponse:
    csv_text = report_service.rows_to_csv(rows, fieldnames)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
