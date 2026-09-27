from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bulk_add_children import CREATED, FAILED, BulkAddChildrenBatch, BulkAddChildrenRow
from app.schemas.child_bulk import BulkChildRowResult


def create_batch(
    db: Session,
    *,
    uploaded_by: str,
    uploaded_file_name: str | None,
    results: list[BulkChildRowResult],
) -> BulkAddChildrenBatch:
    succeeded = sum(1 for r in results if r.status == "created")
    batch = BulkAddChildrenBatch(
        UploadedBy=uploaded_by,
        UploadedFileName=uploaded_file_name,
        TotalRows=len(results),
        SucceededCount=succeeded,
        FailedCount=len(results) - succeeded,
    )
    db.add(batch)
    db.flush()

    for result in results:
        db.add(
            BulkAddChildrenRow(
                BulkUploadID=batch.BulkUploadID,
                RowNumber=result.row_number,
                EmployeeID=result.employee_id,
                ChildName=result.child_name,
                ChildDOBRaw=result.child_dob,
                Status=CREATED if result.status == "created" else FAILED,
                Message=result.message,
                ChildID=result.child_id,
            )
        )
    db.flush()
    return batch


def get_batches(db: Session, *, limit: int = 50) -> list[BulkAddChildrenBatch]:
    return list(
        db.execute(
            select(BulkAddChildrenBatch)
            .order_by(BulkAddChildrenBatch.UploadedDate.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def get_batch_by_id(db: Session, bulk_upload_id: int) -> BulkAddChildrenBatch | None:
    return db.get(BulkAddChildrenBatch, bulk_upload_id)


def get_rows_for_batch(db: Session, bulk_upload_id: int) -> list[BulkAddChildrenRow]:
    return list(
        db.execute(
            select(BulkAddChildrenRow)
            .where(BulkAddChildrenRow.BulkUploadID == bulk_upload_id)
            .order_by(BulkAddChildrenRow.RowNumber)
        )
        .scalars()
        .all()
    )
