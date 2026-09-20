# Business Rules

- Active employee: `Master_Emp_BasicInfo.IsActive = 1` (verified actual column; treat NULL as not active).
- Maximum 2 children per employee.
- ChildID format: `EmployeeId_ChildSequenceNo`.
- Sequence is 1 or 2.
- Monthly benefit: ₹14,000.
- Financial year: April-March.
- Eligibility start month = latest applicable FY start, employee joining month, child birth month.
- Benefit ends at the child's six-year limit: the last eligible month is
  the calendar month containing the child's 6th birthday (inclusive, paid
  in full for that month) — equivalently, the child's 72nd month of life.
  Confirmed by user 2026-09-19; see `DECISIONS_LOG.md` item 12.
- When a child is added, an eligibility record is created for the current
  financial year and, by default, also for the financial year immediately
  following it — unless the six-year/72-month cutoff already falls within
  the current financial year, in which case there is nothing left to
  allot next year and no next-FY record is created. This covers exactly
  one year ahead, at child-creation time; it is not an ongoing rollover
  for existing children in later years. Confirmed by user 2026-09-20; see
  `DECISIONS_LOG.md` item 43.
- Child months 1-12 do not require bills; month is counted from the
  child's date of birth (not from when benefit eligibility began).
  Confirmed by user 2026-09-19; see `DECISIONS_LOG.md` item 17.
- Child month 13+ (from date of birth) normally calls for invoice/receipt
  and payment proof, shown to the employee and HR as informational
  guidance — but this is *not* enforced as a hard block on submission or
  approval "for now," per user direction 2026-09-19; see
  `DECISIONS_LOG.md` item 38.
- Eligibility is automatically calculated when a child is added.
- Claims belong to exactly one employee and child.
- A claim's invoice number must be unique per employee + child, across
  claims of any status. Confirmed by user 2026-09-19; see
  `DECISIONS_LOG.md` item 39.
- An employee may add optional free-text comments when raising a claim
  (`DECISIONS_LOG.md` item 40).
- An employee can view a kid-wise, financial-year-wise eligibility report
  of their own children (Allotted, Utilized, In Progress, Balance, Last
  Modified), computed live from claims the same way as the HR Eligibility
  Utilization report. Confirmed by user 2026-09-19; see
  `DECISIONS_LOG.md` item 41.
- HR actions: Approve, Reject, Send Back.
- HR approved amount must be audited.
- Sent Back claims can be corrected and resubmitted.
- Payout: see `PAYOUT_REQUIREMENTS.md` for the finalized rules
  (confirmed by user 2026-09-20, `DECISIONS_LOG.md` items 44-48) —
  monthly entitlement allocation, within-FY-only carry-forward (never
  across a financial-year boundary), future-month allocation for large
  claims, chronological multi-claim allocation by HR approval time, and
  HR-only manual adjustments. Anything not covered there (actual money
  disbursement, an "Admin" role, claim cancellation) remains unresolved
  and must still not be guessed.
- When HR approves a claim, `Childcare_EligibilityMaster`'s
  ApprovedAmount/UtilizedAmount/InProgressAmount/RemainingAmount for that
  child's financial year are updated to reflect it, and HR cannot approve
  an amount exceeding the current RemainingAmount (Allotted minus
  already-Approved) for that child+FY — in addition to the pre-existing
  rule that it can't exceed the claim's own invoice amount. Submitting,
  rejecting, or sending back a claim also keeps InProgressAmount in sync
  (see `DECISIONS_LOG.md` item 44).
