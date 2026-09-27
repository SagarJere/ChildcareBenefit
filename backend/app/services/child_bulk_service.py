"""Bulk-add-children from a CSV file (user direction 2026-09-26) — the
bulk counterpart to child_service.add_child_for_employee's single-add.

Preview and commit run the *exact same* per-row logic (parse the file,
then call add_child_for_employee for each row, catching the same
business-rule errors) — preview just wraps the whole pass in one more
SAVEPOINT that's unconditionally rolled back at the end, so nothing it
does ever persists, while still exercising every real rule (2-child
cap, duplicate check, eligibility calculation) rather than a separately
maintained approximation of them. Each row gets its own SAVEPOINT so one
row's failure doesn't affect any other row, and a later row's cap/
duplicate check correctly sees earlier rows in the same file that
already succeeded (add_child_for_employee flushes its writes).

commit_bulk_add_children additionally records a permanent audit trail
(Childcare_BulkAddChildrenBatch/Row, user direction 2026-09-26) — never
preview, since preview never actually persists anything.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import (
    BulkFileFormatError,
    BulkRowLimitExceededError,
    DuplicateChildError,
    EmployeeNotFoundError,
    MaxChildrenExceededError,
    MissingJoinDateError,
)
from app.repositories import bulk_add_children_repository
from app.schemas.child_bulk import BulkChildRowResult
from app.services import child_service

REQUIRED_COLUMNS = ("employee_id", "child_name", "child_dob")
MAX_BULK_ROWS = 200


# Tried in order. ISO (unambiguous) first, then the day-first formats
# Excel commonly exports/displays in this locale (India) — "23-12-2023"
# has day=23, so it can only be DD-MM-YYYY, never MM-DD-YYYY. US-style
# MM-DD-YYYY is deliberately NOT accepted: for day <= 12 it would be
# genuinely ambiguous with DD-MM-YYYY and could silently record the
# wrong date of birth instead of failing loudly.
_DOB_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")


def _parse_child_dob(raw: str) -> date | None:
    for fmt in _DOB_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class _ParsedBulkRow:
    # 1-based, counting the header as row 1 (matches how the file looks
    # opened in a spreadsheet).
    row_number: int
    employee_id: str
    child_name: str
    child_dob_raw: str
    child_dob: date | None
    parse_error: str | None


def parse_bulk_child_csv(content: bytes) -> list[_ParsedBulkRow]:
    try:
        text = content.decode("utf-8-sig")  # utf-8-sig strips Excel's BOM if present
    except UnicodeDecodeError as exc:
        raise BulkFileFormatError("The file is not valid UTF-8 text.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise BulkFileFormatError("The file is empty.")

    header_map = {name.strip().lower(): name for name in reader.fieldnames}
    missing = [column for column in REQUIRED_COLUMNS if column not in header_map]
    if missing:
        raise BulkFileFormatError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
        )

    rows: list[_ParsedBulkRow] = []
    for index, raw_row in enumerate(reader, start=2):
        employee_id = (raw_row.get(header_map["employee_id"]) or "").strip()
        child_name = (raw_row.get(header_map["child_name"]) or "").strip()
        child_dob_raw = (raw_row.get(header_map["child_dob"]) or "").strip()

        child_dob: date | None = None
        parse_error: str | None = None
        if not employee_id:
            parse_error = "employee_id is required."
        elif not child_name:
            parse_error = "child_name is required."
        elif not child_dob_raw:
            parse_error = "child_dob is required."
        else:
            child_dob = _parse_child_dob(child_dob_raw)
            if child_dob is None:
                parse_error = (
                    f"child_dob {child_dob_raw!r} is not a valid date "
                    "(expected YYYY-MM-DD or DD-MM-YYYY)."
                )
            elif child_dob > date.today():
                parse_error = "child_dob cannot be in the future."

        rows.append(
            _ParsedBulkRow(
                row_number=index,
                employee_id=employee_id,
                child_name=child_name,
                child_dob_raw=child_dob_raw,
                child_dob=child_dob,
                parse_error=parse_error,
            )
        )

    if not rows:
        raise BulkFileFormatError("The file has no data rows.")
    if len(rows) > MAX_BULK_ROWS:
        raise BulkRowLimitExceededError(
            f"The file has {len(rows)} data rows, which exceeds the limit of "
            f"{MAX_BULK_ROWS} per upload. Split it into smaller files."
        )

    return rows


def _process_rows(
    db: Session, *, rows: list[_ParsedBulkRow], added_by: str
) -> list[BulkChildRowResult]:
    results: list[BulkChildRowResult] = []
    for row in rows:
        if row.parse_error is not None:
            results.append(
                BulkChildRowResult(
                    row_number=row.row_number,
                    employee_id=row.employee_id,
                    child_name=row.child_name,
                    child_dob=row.child_dob_raw,
                    status="failed",
                    message=row.parse_error,
                    child_id=None,
                )
            )
            continue

        assert row.child_dob is not None  # parse_error would be set otherwise
        row_savepoint = db.begin_nested()
        try:
            child = child_service.add_child_for_employee(
                db,
                target_employee_id=row.employee_id,
                child_name=row.child_name,
                child_dob=row.child_dob,
                added_by=added_by,
            )
        except (
            EmployeeNotFoundError,
            MissingJoinDateError,
            MaxChildrenExceededError,
            DuplicateChildError,
        ) as exc:
            row_savepoint.rollback()
            results.append(
                BulkChildRowResult(
                    row_number=row.row_number,
                    employee_id=row.employee_id,
                    child_name=row.child_name,
                    child_dob=row.child_dob.isoformat(),
                    status="failed",
                    message=str(exc),
                    child_id=None,
                )
            )
        else:
            row_savepoint.commit()
            results.append(
                BulkChildRowResult(
                    row_number=row.row_number,
                    employee_id=row.employee_id,
                    child_name=row.child_name,
                    child_dob=row.child_dob.isoformat(),
                    status="created",
                    message=None,
                    child_id=child.child_id,
                )
            )
    return results


def preview_bulk_add_children(
    db: Session, *, rows: list[_ParsedBulkRow], added_by: str
) -> list[BulkChildRowResult]:
    """Runs every row for real, against a SAVEPOINT that's always rolled
    back afterward — so the result reflects exactly what committing
    would do, without anything actually persisting."""
    outer_savepoint = db.begin_nested()
    try:
        return _process_rows(db, rows=rows, added_by=added_by)
    finally:
        outer_savepoint.rollback()


def commit_bulk_add_children(
    db: Session,
    *,
    rows: list[_ParsedBulkRow],
    added_by: str,
    uploaded_file_name: str | None,
) -> list[BulkChildRowResult]:
    """Unlike preview, this also records a permanent
    Childcare_BulkAddChildrenBatch/Row audit trail (user direction
    2026-09-26) — including when every row fails — so a later dispute
    ("I uploaded 2, only 1 was added") can be settled by pointing at
    exactly what happened to each row and why."""
    results = _process_rows(db, rows=rows, added_by=added_by)
    bulk_add_children_repository.create_batch(
        db, uploaded_by=added_by, uploaded_file_name=uploaded_file_name, results=results
    )
    return results
