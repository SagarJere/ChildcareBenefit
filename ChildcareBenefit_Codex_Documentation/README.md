# Childcare Benefit

Production-ready enterprise application.

## Stack
- React + Vite
- FastAPI
- Microsoft SQL Server
- MinIO

## Core Rules
- ₹14,000 per month per eligible child.
- Maximum 2 children per employee.
- Financial year: April through March.
- Eligibility is calculated automatically when a child is added.
- First 12 child months require no bills.
- From child month 13 onward, invoice/receipt and payment proof are mandatory.
- HR can Approve, Reject, or Send Back claims and enter the approved amount.
- Exact payout/carry-forward rules are intentionally not finalized.

## Existing Employee Master
Use `Master_Emp_BasicInfo`:
`MEmpId, EmployeeId, FullName, MysingleID, Gender, Joindate, Inactive`

Do not create a duplicate employee master.

## Quality
No mock production paths, TODO placeholders, hardcoded business data, fake APIs, half-implemented features, or "implement later" executable code.
