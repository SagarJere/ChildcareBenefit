# Project Requirements

## Employee
Use existing `Master_Emp_BasicInfo`.

Version 1 login accepts Employee ID, looks up the employee, and allows only active employees.

## Benefit
- ₹14,000/month/child.
- Maximum two children.
- Benefit until child turns six.

## Financial Year
April 1 through March 31.

## Eligibility Start
For each FY, start in the latest applicable month among:
1. FY April start
2. Employee joining month
3. Child birth month

## Eligibility Trigger
Adding a child must:
1. Validate active employee.
2. Enforce maximum two children.
3. Generate `EmployeeId_1` or `EmployeeId_2`.
4. Save child.
5. Automatically calculate eligibility.
6. Create eligibility atomically.

## Claims
Employee selects a child and provides invoice date, invoice number, invoice amount, receipt/invoice and payment proof.

## Workflow
Submitted → HR Review → Approved / Rejected / Sent Back.

HR can enter approved amount.

## Documents
Months 1-12: no bills required.
Month 13 onward: invoice/receipt and payment proof required.

## Payout
Do not invent payout behavior before final business rules are approved.
