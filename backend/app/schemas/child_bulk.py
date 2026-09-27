from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from app.models import bulk_add_children as bulk_add_children_model

if TYPE_CHECKING:
    from app.models.bulk_add_children import BulkAddChildrenBatch, BulkAddChildrenRow


class BulkChildRowResult(BaseModel):
    row_number: int
    employee_id: str
    child_name: str
    child_dob: str
    status: Literal["created", "failed"]
    message: str | None
    child_id: str | None

    @classmethod
    def from_orm_model(cls, row: BulkAddChildrenRow) -> BulkChildRowResult:
        return cls(
            row_number=row.RowNumber,
            employee_id=row.EmployeeID,
            child_name=row.ChildName,
            child_dob=row.ChildDOBRaw,
            status="created" if row.Status == bulk_add_children_model.CREATED else "failed",
            message=row.Message,
            child_id=row.ChildID,
        )


class BulkAddChildrenResponse(BaseModel):
    total_rows: int
    succeeded: int
    failed: int
    results: list[BulkChildRowResult]

    @classmethod
    def from_results(cls, results: list[BulkChildRowResult]) -> BulkAddChildrenResponse:
        succeeded = sum(1 for r in results if r.status == "created")
        return cls(
            total_rows=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
        )


class BulkUploadBatchSummary(BaseModel):
    bulk_upload_id: int
    uploaded_by: str
    uploaded_file_name: str | None
    total_rows: int
    succeeded_count: int
    failed_count: int
    uploaded_date: datetime

    @classmethod
    def from_orm_model(cls, batch: BulkAddChildrenBatch) -> BulkUploadBatchSummary:
        return cls(
            bulk_upload_id=batch.BulkUploadID,
            uploaded_by=batch.UploadedBy,
            uploaded_file_name=batch.UploadedFileName,
            total_rows=batch.TotalRows,
            succeeded_count=batch.SucceededCount,
            failed_count=batch.FailedCount,
            uploaded_date=batch.UploadedDate,
        )


class BulkUploadBatchDetail(BulkUploadBatchSummary):
    results: list[BulkChildRowResult]
