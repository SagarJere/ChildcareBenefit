# Data Validation Rules

## Employee
Employee ID required, exists and is active.

## Child
Name and DOB required.
Server generates ChildID.
Maximum two children.
Sequence 1 or 2.

## Claim
Child must belong to authenticated employee.
Eligibility must exist.
Invoice date/number/amount required.
Invoice amount and claim amount must be positive.
Month 13+ requires invoice/receipt and payment proof.

## HR
Approved amount must be valid and comply with finalized business rules.
Approval must be atomic and audited.
