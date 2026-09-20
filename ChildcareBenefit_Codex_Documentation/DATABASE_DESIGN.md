# Database Design

## Existing
`Master_Emp_BasicInfo` (verified against the actual `ChildcareBenefit`
database on 2026-09-19 via `INFORMATION_SCHEMA.COLUMNS`; this replaces an
earlier, inaccurate field list that included a `Gender` column and an
`Inactive` flag that do not exist on this table):
- `MEmpID` INT NULL
- `EmployeeID` VARCHAR(20) NULL
- `FullName` VARCHAR(100) NULL
- `MySingleID` VARCHAR(50) NULL
- `Joindate` DATETIME NULL
- `IsActive` BIT NULL

There is no `Gender` column. Active employee check is `IsActive = 1` (not
`Inactive = 0`). All columns are nullable on the existing table; application
code must treat NULL defensively (e.g. a NULL `IsActive` is not active).

Use the exact casing above (`MEmpID`, `EmployeeID`, `MySingleID`) when
defining the SQLAlchemy model for this table, even though SQL Server's
default collation is case-insensitive.

## Childcare_ChildMaster
- ChildID VARCHAR(30) PK
- MEmpId INT NOT NULL
- EmployeeId VARCHAR(20) NOT NULL
- ChildSequenceNo INT NOT NULL
- ChildName VARCHAR(200) NOT NULL
- ChildDOB DATE NOT NULL
- IsActive BIT NOT NULL
- CreatedDate DATETIME2 NOT NULL
- CreatedBy VARCHAR(50) NOT NULL
- UpdatedDate DATETIME2 NULL
- UpdatedBy VARCHAR(50) NULL
- Unique `(MEmpId, ChildSequenceNo)`
- Sequence must be 1 or 2.

## Childcare_FinancialYearMaster
- FinancialYearID INT IDENTITY PK
- FinancialYear VARCHAR(10)
- StartDate DATE
- EndDate DATE
- IsActive BIT
- CreatedDate DATETIME2

## Childcare_EligibilityMaster
- EligibilityID BIGINT IDENTITY PK
- MEmpId
- EmployeeId
- ChildID
- ChildName
- ChildDOB
- FinancialYearID
- FinancialYear
- EligibilityStartDate
- EligibilityEndDate
- EligibleMonths
- MonthlyBenefitAmount DECIMAL(18,2)
- AllottedAmount DECIMAL(18,2)
- UtilizedAmount DECIMAL(18,2)
- ApprovedAmount DECIMAL(18,2)
- InProgressAmount DECIMAL(18,2)
- RemainingAmount DECIMAL(18,2)
- IsActive
- CreatedDate
- UpdatedDate
- Unique `(MEmpId, ChildID, FinancialYearID)`.

## Childcare_ClaimMaster
- ClaimID BIGINT IDENTITY PK
- MEmpId
- EmployeeId
- ChildID
- EligibilityID
- InvoiceDate
- InvoiceNumber
- InvoiceAmount
- ClaimAmount
- ClaimStatus
- Comments (nullable, optional free-text from the employee)
- SubmittedDate
- CreatedDate
- CreatedBy
- UpdatedDate
- UpdatedBy

## Childcare_ClaimAttachments
- AttachmentID BIGINT IDENTITY PK
- ClaimID
- AttachmentType
- OriginalFileName
- StoredFileName
- BucketName
- ObjectKey
- ContentType
- FileSize
- UploadedDate
- UploadedBy

## Childcare_ClaimApprovalHistory
- ApprovalHistoryID BIGINT IDENTITY PK
- ClaimID
- ActionBy
- Action
- PreviousStatus
- NewStatus
- ApprovedAmount
- Remarks
- ActionDate

## Childcare_PayoutMaster
Initial monthly structure may contain employee, child, FY and April-March columns. Exact payout semantics must be finalized before implementation.

## Integrity
Child creation + eligibility creation must be atomic.
Use appropriate indexes for employee, child, FY, claim status and date queries.
