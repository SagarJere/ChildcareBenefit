# MinIO Document Storage

Use MinIO for childcare claim documents. Store metadata/object references in SQL Server.

Bucket:
`childcare-benefit`

Keep bucket private.

Object key:
`claims/{EmployeeId}/{ChildID}/{ClaimID}/{UUID}-{safe-name}`

Example:
`claims/12345678/12345678_1/1001/uuid-invoice.pdf`

## Upload
React → FastAPI → validation → MinIO → SQL metadata.

Validate file size, type and extension. Generate server-side object names.

## Access
FastAPI must authorize access before generating a short-lived pre-signed URL or streaming the file.

Employees can access only their own documents. HR access must be role-authorized.

Consider malware scanning for production.

Use environment-based MinIO configuration. No credentials in source.
