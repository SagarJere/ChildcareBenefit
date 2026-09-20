# Testing Strategy

## Unit
Test:
- Financial year
- Eligibility start/end
- Joining scenarios
- Child DOB scenarios
- Six-year limit
- Eligible months
- ₹14,000 calculation
- Two-child limit
- Child ID generation
- Month 1-12 document rule
- Month 13+ document rule
- Claim status transitions

## Integration
Test SQL Server repositories, child+eligibility transaction, claims, HR workflow and MinIO.

## API
Test authentication, authorization, ownership, validation, pagination and status transitions.

## Negative
Test unknown/inactive employee, third child, unauthorized access, invalid dates, invalid/oversized files and concurrent approval.

## Definition of Done
Code + validation + authorization + tests + integration + documentation complete.
No placeholder production logic.
