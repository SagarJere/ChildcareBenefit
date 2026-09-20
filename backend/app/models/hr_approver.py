from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class HRApprover(Base):
    """Access-control table: an EmployeeID present here with IsActive=1
    may view and act on HR claim-review endpoints. Not a foreign key to
    Master_Emp_BasicInfo — see ChildMaster.MEmpID for why. Managed
    directly by a DBA; this application has no HR-approver management UI.
    """

    __tablename__ = "Childcare_HRApprovers"

    HRApproverID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    EmployeeID: Mapped[str] = mapped_column(unique=True)
    IsActive: Mapped[bool] = mapped_column(default=True)
    CreatedDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.getutcdate())
