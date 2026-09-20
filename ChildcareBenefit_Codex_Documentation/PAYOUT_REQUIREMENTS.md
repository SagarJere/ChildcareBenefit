# Payout Calculation & Adjustment Requirements

Finalized 2026-09-20, confirmed directly by the user. This document
resolves `CODEX_MASTER_INSTRUCTIONS.md` §12 ("the exact payout and
carry-forward rules are NOT finalized... do not invent payout
behavior") for the scope described here. Anything not covered by this
document is still unresolved and must not be guessed — stop and ask.

See `DECISIONS_LOG.md` items 45+ for the discussion/reasoning behind each
rule below.

## 1. Objective

A payout calculation module that provides:

- Monthly entitlement calculation, financial-year-wise (April → March)
- Allocation of each approved claim across the current and future eligible
  months it needs to fully pay out
- A per-child, per-financial-year monthly payout schedule (Apr–Mar)
- Full traceability from "what was approved" to "which month it pays out
  in"
- Controlled manual adjustments (HR-only for now)
- A clear employee-facing view of when an approved claim will actually be
  paid

## 2. Monthly Entitlement

Each eligible child receives **₹14,000 per eligible month**
(`eligibility_calculator.MONTHLY_BENEFIT_AMOUNT`), for exactly the months
already identified as eligible by the existing eligibility calculation
(`EligibilityMaster.EligibilityStartDate`...`EligibilityEndDate`, which
already accounts for financial year, employee join date, child DOB, and
the six-year/72-month cutoff — see `BUSINESS_RULES.md`). The payout
module does not recompute *which* months are eligible; it consumes that
existing result.

## 3. Carry Forward — within a financial year only

Unused entitlement carries forward from month to month **within the same
financial year**. It does **not** carry forward across a financial-year
boundary — confirmed by user 2026-09-20 (see `DECISIONS_LOG.md` item 45).
Any entitlement unused by the end of March is forfeited; the next
financial year's ledger always starts with a zero opening balance,
regardless of how much of the prior year went unused.

This means:

- `Childcare_PayoutMonthlyLedger` rows never need to reference another
  financial year — no cross-FY chaining.
- A single approved claim's allocation is always fully contained within
  one financial year (see §6 for why this is mathematically guaranteed,
  not just a rule to enforce).

## 4. Claims Can Consume Future Entitlement (within the FY)

An approved claim's amount may exceed the entitlement accumulated so far
in the financial year. The excess is allocated to the child's future
eligible months within the *same* financial year, in calendar order,
until the full approved amount is allocated or the financial year (or the
child's eligibility end date, if earlier) is reached.

Example (child eligible from September, ₹14,000/month):

| Month | Entitlement | Carry-in | Available | Claim | Allocated | Carry-out |
| ----- | ----------: | -------: | --------: | ----: | --------: | --------: |
| Sep   |     ₹14,000 |       ₹0 |   ₹14,000 |₹9,000 |    ₹9,000 |    ₹5,000 |
| Oct   |     ₹14,000 |   ₹5,000 |   ₹19,000 |    ₹0 |        ₹0 |   ₹19,000 |
| Nov   |     ₹14,000 |  ₹19,000 |   ₹33,000 |₹50,000|   ₹33,000 |        ₹0 |
| Dec   |     ₹14,000 |       ₹0 |   ₹14,000 |  (cont.)|  ₹14,000 |        ₹0 |
| Jan   |     ₹14,000 |       ₹0 |   ₹14,000 |  (cont.)|   ₹3,000 |   ₹11,000 |

(The ₹50,000 claim approved "in November" allocates ₹33,000 in Nov,
₹14,000 in Dec, ₹3,000 in Jan — total ₹50,000.)

## 5. Multiple Claims — chronological by HR approval time

When a child has multiple approved claims, they are allocated **in the
order HR approved them** (`Childcare_ClaimApprovalHistory.ActionDate` for
the `Approved` entry — not invoice date, not claim-creation date). Each
claim consumes whatever entitlement remains *after* all earlier-approved
claims have already been allocated.

Continuing the example above: a second claim of ₹15,000 approved later
allocates against whatever is left after the first claim — ₹11,000 into
January (topping up the ₹3,000 already there) and ₹4,000 into February.
**The original claim's `ApprovedAmount` on `Childcare_ClaimMaster` never
changes** — only how it's *broken down across months*
(`Childcare_PayoutAllocation`) can be recalculated.

## 6. Eligibility Boundary

Allocation never extends into a month the child isn't eligible for
(before `EligibilityStartDate`, after `EligibilityEndDate`, or outside the
financial year). Because HR approval is already capped at the *total*
remaining balance for that child+FY (`EligibilityMaster.RemainingAmount`,
see `DECISIONS_LOG.md` item 44), and total balance equals exactly the sum
of that FY's own eligible months' entitlement, a valid allocation
**always exists fully within the same financial year** — it is
mathematically impossible for a single (child, FY)'s approved claims to
need more months than that FY actually has. This was verified by
analysis, not just assumed, before finalizing item 45's "no cross-FY
carry-forward" rule.

## 7. Recalculation

Only two events trigger a recalculation of a child+FY's payout schedule:

1. A new claim is approved for that child+FY.
2. An approved payout adjustment is recorded against that child+FY.

Per user direction 2026-09-20 (see `DECISIONS_LOG.md` item 46): **an
Approved claim's status is terminal.** There is no "un-approve",
"cancel", or "reject after approval" — those triggers from an earlier
draft of this spec are explicitly out of scope. This means recalculation
is always a forward-only, additive replay: every approved claim for a
child+FY, in approval-time order, followed by every adjustment for that
child+FY.

**Strategy: full rebuild, not incremental.** `Childcare_
PayoutMonthlyLedger` and `Childcare_PayoutAllocation` are treated as pure,
disposable, derived data — never hand-edited, always safe to delete and
regenerate in full from the two real, immutable, append-only sources of
truth: `Childcare_ClaimApprovalHistory` (already exists) and `Childcare_
PayoutAdjustment` (new). This matches the same "recompute from scratch,
never an incremental delta" principle already used for `Childcare_
EligibilityMaster`'s balance columns (`eligibility_balance_service.
sync_balance`, `DECISIONS_LOG.md` item 44), for the same reason: it makes
the result deterministic and immune to drift from a missed edge case,
which matters more here than the (still negligible, at this
application's scale) extra compute cost of recomputing from scratch.

## 8. Payout Adjustments — not yet built

HR (the existing `Childcare_HRApprovers` role — see `DECISIONS_LOG.md`
item 47) will be able to record a manual correction to a specific
child+FY+month's calculated payout. Per user direction 2026-09-20:

- **No maker-checker.** An HR approver can both create and have an
  adjustment take effect immediately — there is no separate
  request-then-approve workflow for v1.
- **"Admin" is deferred.** The user mentioned a future distinct "Admin"
  role that may also get this capability; it is not yet defined and is
  out of scope until specified.
- **No amount validation ("trust the HR"), confirmed 2026-09-20** (see
  `DECISIONS_LOG.md` item 50): an adjustment is not bounded or checked
  against anything — no guard against pushing a month's closing balance
  negative, no cap relative to the entitlement or allotted amount. HR is
  trusted completely.
- **Not yet implemented.** `Childcare_PayoutAdjustment`,
  `AdjustmentAmount` actually being populated (it exists as a column on
  `Childcare_PayoutMonthlyLedger`, always 0 today), and any endpoint/UI
  for recording one are all still to be built.
- Adjustments are **append-only and immutable** — never edited or
  deleted. Correcting a previous adjustment means recording a new,
  opposite/compensating adjustment, never modifying the original. Reason
  and remarks are both mandatory on every adjustment.
- Both positive and negative adjustment amounts are supported.
- An adjustment is a delta applied on top of the calculated
  (claims-only) allocation for that month, producing the final payout
  figure for that month — it never changes `Childcare_ClaimMaster` or
  `Childcare_PayoutAllocation`.

## 9. Audit

Per user-confirmed simplification (see `DECISIONS_LOG.md` item 48): a
dedicated `Childcare_PayoutAudit` table is **deferred, not built in the
first cut**. The two real triggers are already independently,
permanently, and immutably recorded:

- Claim approvals: `Childcare_ClaimApprovalHistory` (existing).
- Adjustments: `Childcare_PayoutAdjustment` itself is the audit record
  (who, when, reason, remarks, original/adjustment/revised amounts) —
  since adjustments are append-only, no separate log is needed to know
  "what was adjusted, by whom, why, and when."

Because the ledger and allocation tables are fully and deterministically
re-derivable from those two sources at any time, "what did the engine
calculate before vs. after a given recompute" is answerable on demand
(re-run the engine with the claims/adjustments as of any point in time)
rather than needing its own change-log table. If a concrete auditability
gap is found once this is in use, a dedicated audit table can be added
later without disrupting the ledger/allocation design.

## 10. Proposed Database Design

Column names follow this project's existing convention (`MEmpID`,
`ChildID`, `EligibilityID`, `FinancialYearID` — matching `Childcare_
ClaimMaster`/`Childcare_EligibilityMaster`, not the `MEmpId` casing from
an earlier draft of this spec).

### Childcare_PayoutMonthlyLedger

One row per Employee + Child + Financial Year + Month. Purely derived —
rebuilt in full on every recalculation for that child+FY.

- PayoutLedgerID, MEmpID, EmployeeID, ChildID, EligibilityID,
  FinancialYearID, FinancialYear, PayoutMonth (a calendar month/year, not
  just "Apr"/"May" — e.g. 2026-09), EntitlementAmount, OpeningBalance,
  CarryForwardAmount, TotalAvailableAmount, ClaimAllocatedAmount,
  AdjustmentAmount, ClosingBalance, CalculatedPayoutAmount, CreatedDate,
  UpdatedDate.
- `ClaimAllocatedAmount` is the pure, claims-only engine output;
  `AdjustmentAmount` is the sum of approved adjustments for that month;
  `CalculatedPayoutAmount` = `ClaimAllocatedAmount` + `AdjustmentAmount`
  (the actual final payout figure for that month).
- No `LedgerStatus` column for v1 — every row is always the current,
  fully-recomputed state; there is no separate draft/final workflow yet.

### Childcare_PayoutAllocation

Records which approved claim consumed which month's entitlement. One
approved claim can produce multiple rows (one per month it pays out
across). Purely derived — rebuilt in full alongside the ledger.

- PayoutAllocationID, ClaimID, PayoutLedgerID, MEmpID, EmployeeID,
  ChildID, EligibilityID, FinancialYearID, PayoutMonth,
  AllocationSequence, AllocatedAmount, CreatedDate.
- No `AllocationStatus` column for v1, for the same reason as
  `LedgerStatus` above.

### Childcare_PayoutAdjustment

Append-only manual corrections. Never edited or deleted after creation.

- AdjustmentID, MEmpID, EmployeeID, ChildID, EligibilityID,
  FinancialYearID, PayoutMonth, OriginalAmount, AdjustmentAmount,
  RevisedAmount, Reason (mandatory), Remarks (mandatory), CreatedBy,
  CreatedDate.
- No maker-checker fields (`RequestedBy`/`ApprovedBy`/`ApprovedDate`) for
  v1, per §8 — the creator's action is immediately effective.

### Childcare_PayoutSummary — table deferred; the report it was for now exists

A pivoted Apr–Mar *table* exists in the original draft spec for
reporting. Per §17 of the original spec (and confirmed by this
document's overall design), this is explicitly **not** a source of
truth and must never be edited directly — it would be a generated cache
of `Childcare_PayoutMonthlyLedger`. The stored table itself is still not
built (and may never need to be) — but the report it was meant to serve
now exists as a live query: `GET /hr/reports/payout` (added 2026-09-20,
see `DECISIONS_LOG.md` item 50) returns exactly this Employee + Child +
FY, Apr-Mar shape, computed on demand from `Childcare_
PayoutMonthlyLedger` rather than a separate stored table — the same
"live report" pattern every other HR report already uses. Filterable by
financial year, employee ID, and child ID; on-screen table plus CSV
export.

## 11. Explicit Non-Goals (for now)

- Cross-financial-year carry-forward (§3 — confirmed: none).
- Reversing/cancelling an already-Approved claim (§7 — confirmed: not
  supported; Approved is terminal).
- `Childcare_PayoutAdjustment` itself, and any endpoint/UI to create one
  (§8 — not yet built; its validation rule — none, "trust the HR" — is
  already confirmed for whenever it is).
- A distinct "Admin" role (§8 — deferred, undefined).
- Adjustment maker-checker workflow (§8 — confirmed: not required).
- A dedicated `Childcare_PayoutAudit` table (§9 — deferred).
- The stored `Childcare_PayoutSummary` *table* (§10 — deferred; the
  report it was meant to serve is already live at `GET
  /hr/reports/payout`, computed on demand instead).
- Actual money disbursement / payroll integration ("Actual Payment" in
  the original spec's terminology) — this module only tracks *when an
  approved claim's money should be considered due*, not real-world
  payment execution.

## 12. Separation of Concepts

(Unchanged from the original spec — kept here verbatim as it's a useful
reference.)

- **Entitlement** — amount the employee becomes eligible to receive for a
  month.
- **Claim** — expense amount submitted by the employee.
- **Approved Claim** — amount approved by HR (`ClaimMaster.ClaimStatus =
  Approved`, amount recorded in `ClaimApprovalHistory.ApprovedAmount`).
- **Payout Allocation** — how an approved claim's amount is distributed
  across eligible months (`Childcare_PayoutAllocation`).
- **Monthly Ledger** — the child's monthly entitlement and running
  balance for a financial year (`Childcare_PayoutMonthlyLedger`).
- **Adjustment** — an authorized manual correction to the calculated
  payout for a specific month (`Childcare_PayoutAdjustment`).
- **Actual Payment** — real-world disbursement by payroll/finance, not in
  scope for this module.
