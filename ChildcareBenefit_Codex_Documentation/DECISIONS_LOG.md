# Architecture Decisions

1. Use existing `Master_Emp_BasicInfo`.
2. Use `MEmpId` for internal relationships where data types permit.
3. ChildID format is `EmployeeId_ChildSequenceNo`.
4. Store documents in private MinIO; metadata in SQL Server.
5. React + Vite for frontend.
6. FastAPI for backend.
7. Eligibility is automatically calculated when a child is added.
8. Payout is not implemented until its business rules are finalized.
9. On 2026-09-19, connected to the actual local `ChildcareBenefit` SQL
   Server database and inspected `Master_Emp_BasicInfo` via
   `INFORMATION_SCHEMA.COLUMNS`. The real table differs from what earlier
   documentation described: there is no `Gender` column, and the active
   flag is `IsActive` (BIT, active = 1), not `Inactive` (active = 0). Per
   user confirmation, the actual table is authoritative — `DATABASE_DESIGN.md`,
   `LOGIN_REQUIREMENTS.md`, `BUSINESS_RULES.md`, and
   `CODEX_MASTER_INSTRUCTIONS.md` §5/§6 were updated to match it, and
   `Gender` is dropped from anything Employee Login returns.
10. The backend SQL Server config supports both SQL authentication
    (`MSSQL_AUTH_MODE=sql`, with username/password) and Windows/trusted
    authentication (`MSSQL_AUTH_MODE=windows`), and `MSSQL_PORT` is
    optional so a local named/default-instance connection can use shared
    memory instead of TCP. This was needed because the local dev SQL
    Server instance is reachable via Windows Authentication and direct TCP
    to it times out (a local firewall/instance-configuration issue, not
    something the application can work around beyond preferring the
    protocol that works).
11. Employee Login (Increment 2) issues a short-lived signed JWT as the
    "authentication/session boundary" required by
    `CODEX_MASTER_INSTRUCTIONS.md` §6 — no session mechanism was specified
    in the documentation, and this was not a materially ambiguous business
    rule, so a standard, maintainable choice was made rather than asking.
    A bearer token (not a server-side session or cookie) was chosen
    because: (a) it fits a stateless REST/JSON API, and (b) it keeps the
    same shape (a verified bearer credential naming an identity) that an
    approved SSO/Entra ID token would have, so swapping the issuer later
    should not require reworking how the rest of the backend consumes
    identity. Every protected endpoint re-reads the employee's current
    `IsActive` status from the database on each request rather than
    trusting the token for anything beyond identity, so deactivating an
    employee takes effect immediately rather than waiting for token
    expiry.
12. Six-year eligibility cutoff (confirmed by user 2026-09-19, since
    `CODEX_MASTER_INSTRUCTIONS.md` §7's "six-year eligibility limit" did
    not specify exact granularity and this materially affects money/month
    calculations): the last eligible month is the calendar month
    containing the child's 6th birthday, paid in full (no proration) —
    consistent with eligibility start already being expressed as "the
    latest applicable month" rather than an exact date.
13. Only the *current* financial year's eligibility record is calculated
    and created when a child is added (per `CODEX_MASTER_INSTRUCTIONS.md`
    §8's singular "the eligibility record"). No document describes a
    rollover/renewal process that creates next year's `Childcare_
    EligibilityMaster` row automatically — that is out of scope here and
    must not be invented; it is left for a future increment when its
    business rules are specified.
14. `Master_Emp_BasicInfo` has no primary key or unique constraint (see
    item 9), so `Childcare_ChildMaster.MEmpID` cannot carry a real foreign
    key to it — SQL Server requires the referenced column to be a PK or
    have a unique constraint. It is a plain indexed `INT` column instead.
    `Childcare_EligibilityMaster.ChildID` and `.FinancialYearID` do use
    real foreign keys, since `Childcare_ChildMaster` and `Childcare_
    FinancialYearMaster` are new tables this application owns and controls.
15. `Childcare_FinancialYearMaster` rows are computed and get-or-created by
    the eligibility service the first time a given financial year is
    needed, rather than requiring a DBA to pre-seed them — this is a
    mechanical data-provisioning detail, not a business rule, so a
    standard maintainable choice was made rather than asking.
16. If an employee's `Joindate` is NULL (verified possible — see item 9),
    adding a child fails with a clear 400 error rather than silently
    guessing a fallback join date, since join date directly drives the
    eligibility-start calculation.
17. "Child month" for the months 1-12 (no bills) / month 13+ (bills
    required) rule (confirmed by user 2026-09-19) is counted from the
    child's date of birth, not from when benefit eligibility began. A
    child enrolled late (e.g. at age 3) is therefore already past month
    12 and needs documents from their very first claim.
18. `ClaimMaster.ClaimAmount` is set equal to `InvoiceAmount` at claim
    creation — `CODEX_MASTER_INSTRUCTIONS.md` §9's list of employee-
    provided claim data does not include a separate claim-amount input,
    only invoice date/number/amount and the two documents. This does not
    touch the unresolved payout/approval-amount rules (§12) — HR's
    separate `ApprovedAmount` (Increment 5) is where any deviation from
    the invoice amount will be decided, once that business rule exists.
19. A claim's `EligibilityID` is resolved by matching the claim's invoice
    date to the financial year it falls in and looking up that child's
    eligibility record for that FY — not simply "the child's current
    eligibility" — since a claim's invoice date determines which
    eligibility period it belongs to. Because only the current FY's
    eligibility is created per child (item 13), a claim for a financial
    year with no eligibility record for that child is rejected with a
    clear "no eligibility for this period" error; this is a direct,
    literal reading of `DATA_VALIDATION_RULES.md`'s "Eligibility must
    exist" rule, not an invented restriction.
20. This increment's claim/attachment logic does not read or write
    `Childcare_EligibilityMaster.UtilizedAmount`, `.ApprovedAmount`,
    `.InProgressAmount`, or `.RemainingAmount`. `CODEX_MASTER_
    INSTRUCTIONS.md` §12 explicitly forbids guessing "interaction between
    approved and pending claims" and similar payout mechanics — those
    fields remain whatever they were set to when the eligibility record
    was created, until the HR approval workflow (Increment 5) and the
    still-unresolved payout rules define how they change.
21. No local MinIO instance is available in this environment and Docker
    is not installed; per user direction (2026-09-19) the user will
    install/run MinIO themselves and provide connection details. Document
    upload/download code is implemented and unit-tested now; the
    integration tests that exercise real MinIO uploads are written to
    skip cleanly (not fake) when `MINIO_*` is not configured, the same
    pattern already used for SQL-Server-dependent tests.
22. Upload limits (max file size, allowed extensions) are not specified
    in any document — these are operational parameters, not a business
    rule, so a standard default was chosen and made configurable:
    10 MB max, PDF/JPG/JPEG/PNG only (`MAX_UPLOAD_SIZE_MB`,
    `ALLOWED_UPLOAD_EXTENSIONS`).
23. `GET /claims/{claimId}/attachments/{attachmentId}/download` was added
    beyond `API_SPECIFICATION.md`'s literal endpoint list, the same way
    `POST /children/preview-eligibility` was added in Increment 3 —
    `MINIO_DOCUMENT_STORAGE.md` explicitly requires authorized access to
    the actual file content ("generate a short-lived pre-signed URL or
    stream the file"), which is not possible through any endpoint in the
    original list.
24. MinIO's official binary distribution (dl.min.io) was discontinued
    between this project's Increment 1 (2026-09-19) and Increment 4
    (2026-09-19, later the same day) — the open-source MinIO Server
    project was archived and its downloads return HTTP 410 Gone; this is
    upstream reality, not a decision this project made. For local
    development on this machine, the last pre-archival Windows binary
    (RELEASE.2025-01-18) was retrieved from the Internet Archive's Wayback
    Machine (an exact, unmodified capture of the real dl.min.io release)
    and installed at `.minio/bin/minio.exe`, gitignored, with local data
    at `.minio/data/`. This has no bearing on the application code, which
    talks to any S3-compatible endpoint via `MINIO_*` settings — a real
    MinIO/S3-compatible deployment elsewhere (or a newer distribution
    channel, if MinIO establishes one) is a drop-in replacement with no
    code changes. See `README.md` for how to start/stop it.
25. HR authorization source (Increment 5, per user direction 2026-09-19):
    a dedicated `Childcare_HRApprovers` table (`HRApproverID`,
    `EmployeeID` unique, `IsActive`, `CreatedDate`) — an EmployeeID present
    here with `IsActive = 1` may view and act on `/hr/*` endpoints; no
    other employee can, regardless of anything in the frontend. This
    table has no management UI in this application; a DBA manages it
    directly (matching how `Master_Emp_BasicInfo` itself is managed
    outside this app). The table starts empty — no HR approver is seeded,
    since deciding who has HR access is the organization's call, not
    something to guess. `EmployeeID` is not a foreign key to
    `Master_Emp_BasicInfo`, for the same reason as `Childcare_ChildMaster.
    MEmpID` (item 14).
26. Approving a claim validates `approved_amount > 0` and `<= InvoiceAmount`
    — a single-claim sanity check, not a payout-aggregation rule, so it
    doesn't touch the §12 boundary (item 20). The approved amount is
    recorded only in `Childcare_ClaimApprovalHistory` (per
    `DATABASE_DESIGN.md`, `Childcare_ClaimMaster` itself has no
    ApprovedAmount column) — it is not written back onto the claim or
    onto `Childcare_EligibilityMaster`.
27. Per `CODEX_MASTER_INSTRUCTIONS.md` §9 ("A Sent Back claim can be
    corrected and resubmitted"), the employee-side edit/submit endpoints
    (previously Draft-only) now also accept a `SentBack` claim — this was
    a real gap fixed as part of building HR Send Back, since without it
    Send Back would be a dead end.
28. HR approve/reject/send-back only ever transition a claim directly
    from `Submitted`; the `HRReview` status value (already in the
    `ClaimStatus` CHECK constraint from Increment 4) is never actually
    set. No document describes a distinct "HR opens this claim" action
    that would populate it, and `API_SPECIFICATION.md` lists no such
    endpoint — inventing one would be adding undocumented API surface for
    pure workflow ceremony with no effect on outcomes.
29. Remarks are required (non-empty) for Reject and Send Back, optional
    for Approve — not stated explicitly anywhere, but a standard,
    low-risk default: an employee needs to know why a claim was rejected
    or sent back, and enforcing it costs nothing.
30. HR approvers are not restricted from approving their own claims
    (no self-review conflict-of-interest check). No document requests
    this, and it isn't a natural consequence of anything specified, so it
    was left out rather than invented — noted here so it can be revisited
    if the organization wants that control.
31. Reports (Increment 6, user direction 2026-09-19): scope was almost
    entirely unspecified in the docs (only a name in `FRONTEND_
    ARCHITECTURE.md`'s HR screen list and a roadmap bullet), so the user
    was asked directly rather than guessed. Confirmed: Claims Summary +
    Eligibility Utilization + Employee/Child Headcount, each with an
    on-screen table and CSV export (CSV, not a genuine `.xlsx`, since CSV
    opens natively in Excel and needs no extra dependency — a standard
    implementation choice, not asked about separately).
32. Eligibility Utilization report values are computed live for display
    (SUM of `Childcare_ClaimApprovalHistory.ApprovedAmount` for that
    eligibility's Approved claims; SUM of `Childcare_ClaimMaster.
    ClaimAmount` for its Submitted claims) — never read from or written to
    `Childcare_EligibilityMaster`'s own Utilized/Approved/InProgress/
    RemainingAmount columns, which per items 20/26 are never updated by
    this application and would misleadingly show zero for every record.
    The report shows "Allotted", "In Progress" (Submitted claims total),
    and "Approved" (Approved claims total) as three independent figures,
    plus "Remaining after approved" = Allotted − Approved. It does not
    compute a single balance that also subtracts in-progress claims,
    since whether a pending claim reserves against the remaining balance
    is exactly the kind of "interaction between approved and pending
    claims" §12 forbids guessing.
33. Reports are HR-only (`FRONTEND_ARCHITECTURE.md` lists "Reports" under
    the HR screen list, not Employee), gated by the same
    `get_current_hr_approver` dependency as the rest of Increment 5.
34. The Headcount report's "by financial year" breakdown groups children
    by their (only) existing eligibility record's financial year — i.e.
    the year they were originally enrolled — not a "current status per
    year" view, since (per item 13) no rollover process creates
    subsequent years' eligibility records. Labeled accordingly in the UI
    to avoid implying a capability that doesn't exist.
35. Increment 7 (Security & Performance Testing) was scoped directly from
    `SECURITY.md`'s explicit checklist — unlike Reports, this needed no
    clarifying question since the checklist already defines what to
    verify. Audited and confirmed clean: no hardcoded secrets, all SQL
    goes through the ORM's parameterized `select()` (no raw/f-string
    SQL), CORS is restricted to configured origins (no wildcard), no
    logging of passwords/tokens/document contents or request bodies, and
    every non-public route (all but `/auth/login` and `/health`) carries
    the correct `get_current_employee` or `get_current_hr_approver`
    dependency (cross-checked by counting route decorators against
    dependency usages per file).
36. Two items from `SECURITY.md`/`DEPLOYMENT.md` are operational/
    infrastructure decisions this application's code cannot itself
    provide: a least-privilege SQL Server login (the code only ever
    issues ordinary SELECT/INSERT/UPDATE through the ORM — provisioning
    a restricted login for it is a DBA task against the real production
    server) and HTTPS (needs a real certificate and domain, normally
    terminated at a reverse proxy in front of this app — see
    `DEPLOYMENT.md`). Both are called out here rather than silently
    skipped or faked.
37. `hr_service.list_claims` had a real N+1 query pattern (one query for
    the child and one for the employee's name, per claim in the result)
    — found and fixed during this increment's review by batching both
    lookups once per request, the same pattern already used in
    `report_service.py`. This mattered here specifically because the HR
    queue's result set grows with total claims across *all* employees,
    unlike an employee's own claims list (bounded by their own small
    claim history) — a query-count regression test now locks this in.
38. Post-Increment-7 improvement, user direction 2026-09-19: the
    document-upload requirement (receipt/invoice + payment proof for the
    child's 13th month or later — `BUSINESS_RULES.md` line 17-18) is no
    longer enforced as a submission blocker, "for now." `claim_service.
    submit_claim` no longer raises on missing documents; the
    `MissingRequiredDocumentsError` exception class was removed (nothing
    raises it) rather than left dead in the codebase. The `requires_documents`
    flag is still computed and returned to both the employee and HR
    clients, purely informational — the Raise Claim wizard's Step 3 and
    the HR claim-detail page's "missing document" note both still show
    it, but neither blocks progression/approval on it anymore. Since this
    was explicitly framed as temporary ("for now"), re-enabling the block
    later is a two-line change: re-add the check in `submit_claim` using
    `claim_attachment_repository.get_for_claim` and the required-types set.
39. Post-Increment-7 improvement, user direction 2026-09-19: claim
    creation and editing now reject a duplicate invoice number for the
    same employee + child combination (`claim_repository.get_by_invoice`,
    raising `DuplicateInvoiceError` -> HTTP 409). Scope decision (not
    specified by the user, so decided as the simplest literal reading):
    the check considers *any* existing claim regardless of status (Draft,
    Submitted, Approved, Rejected, SentBack) — not just active ones. This
    means a Rejected claim's invoice number can never be reused in a new
    claim; if that turns out to be too restrictive in practice (e.g. HR
    rejects for an unrelated reason and the employee needs to resubmit
    under a new claim), the scope can be narrowed by excluding Rejected
    claims from `get_by_invoice`'s lookup. On update, the claim being
    edited excludes itself from the duplicate search.
40. Post-Increment-7 improvement, user direction 2026-09-19: added an
    optional `Comments` column to `Childcare_ClaimMaster` (nullable,
    VARCHAR(1000), migration `b6e682ad8a0d`) so an employee can add
    free-text context while raising a claim. Deliberately named
    `Comments` (not `Remarks`) to stay visually distinct from HR's
    `Childcare_ClaimApprovalHistory.Remarks`, which is a different actor
    (HR, not the employee) recorded at a different point (approval
    action, not claim creation). Surfaced read-only to HR on the claim
    detail view for context; not required, and not editable by HR.
41. Post-Increment-7 improvement, user direction 2026-09-19: added a
    kid-wise, financial-year-wise eligibility report for employees
    (`GET /api/v1/eligibility/report`, `EligibilityReportPage.tsx` at
    `/eligibility`), showing Allotted / Utilized / In Progress / Balance /
    Last Modified per child per financial year. Reuses the exact
    live-computed-from-claims approach already established for the HR
    Eligibility Utilization report (item 32) rather than
    `EligibilityMaster`'s own never-updated balance columns — "Utilized"
    here is the sum of HR-approved claim amounts (same figure the HR
    report calls "Approved") and "Balance" is Allotted minus Utilized
    (same as the HR report's "remaining after approved"), just relabeled
    to match the user's requested column names. "Last Modified" is new:
    since `EligibilityMaster.CreatedDate` never changes after the row is
    created, it's computed as the latest of that child's claims'
    created/updated/submitted dates and any HR approval-history action
    date against them (`report_repository.get_last_activity_by_eligibility`),
    falling back to the eligibility row's own `CreatedDate` when no claim
    activity exists yet. Lives under `/eligibility/report` (employee
    auth), not `/hr/reports` (HR-only auth) — it's the same computation
    audience-scoped differently, not an HR report. Route order matters:
    it's registered before `/eligibility/{child_id}` so "report" isn't
    swallowed as a child ID (regression-tested). No CSV export was added,
    since the user only asked to view the report on-screen.
42. User-requested login-page autocomplete (2026-09-19): before building
    it, the user was warned that this directly conflicts with the
    deliberate no-enumeration design already in place (`AuthenticationError`'s
    docstring; the Increment 7 security audit explicitly checks that login
    can't be used to enumerate valid Employee IDs) — a public, pre-login
    autocomplete necessarily exposes the active-employee roster to anyone
    who can reach the API, not just people who can log in. Given the
    choice between accepting that tradeoff, a throttled/partial version,
    or not building it, the user chose to accept the full tradeoff. Added
    `GET /auth/active-employees` (no auth dependency, deliberately public,
    returns EmployeeID + FullName for every `IsActive = 1` employee with a
    non-null EmployeeID) and a combobox on the login page that filters
    this list client-side as the user types, while still allowing free
    typing (falls back gracefully if the list fails to load or an
    employee isn't in it). This is a real, accepted security posture
    change for this application — if the threat model changes later
    (e.g. this moves from an internal-network tool to something
    internet-facing), this endpoint should be revisited.
43. Eligibility rollover (user direction 2026-09-20): item 13 had
    explicitly deferred any "rollover/renewal process that creates next
    year's `Childcare_EligibilityMaster` row" as out of scope pending
    business-rule clarification. The user has now specified it, at least
    partially: `add_child` creates an eligibility record for the current
    financial year **and**, by default, the financial year immediately
    following it — capped at the child's 72nd month (6th birthday/
    six-year limit, `SIX_YEAR_LIMIT_YEARS`, already the existing cutoff
    rule). If that 72-month cutoff already falls within the current
    financial year, the next-FY record is skipped entirely, since it
    would carry zero eligible months/allotted amount anyway
    (`eligibility_calculator.next_financial_year_needed`/
    `next_financial_year_window`). This is scoped narrowly to exactly
    "current + one year ahead" at child-creation time — it is **not** an
    ongoing scheduled/triggered rollover that keeps extending eligibility
    year after year for as long as a child remains under six. A child
    that outlives that pre-created next-FY record (i.e., is still under
    six two or more financial years after being added) will still hit
    `NoEligibilityForPeriodError` when a claim is raised against a
    financial year with no record, exactly as before — a genuine
    standing/recurring rollover mechanism for existing children over
    multiple years was not requested and has not been built; it would
    need its own trigger (e.g. a scheduled job, or lazily creating the
    record when a claim needs a FY that doesn't have one yet) and should
    be raised as a separate, explicit request if needed. Existing
    children added before this change do not retroactively get a next-FY
    record — only new additions do, unless a backfill is requested.
    `GET /eligibility`, `GET /eligibility/{child_id}`, and the employee
    eligibility report (item 41) all already return every eligibility
    row for a child/employee (not scoped to the current FY), so the new
    next-FY row is visible through existing endpoints/pages with no
    further UI changes needed. The "Add Child" eligibility preview
    (`POST /children/preview-eligibility`) still shows only the current
    FY's figures and was not changed to also preview the next-FY
    allotment — a minor, known gap, not addressed since it wasn't asked
    for.
44. Payout tracking, first slice (user direction 2026-09-20): items 20/26/
    32 had all deliberately kept `Childcare_EligibilityMaster`'s
    UtilizedAmount/ApprovedAmount/InProgressAmount/RemainingAmount frozen
    at their initial values, since payout mechanics (§12) were unresolved
    and the HR/employee reports computed their own figures live from
    claims instead. The user has now specified enough of the rule to
    maintain these columns for real: on every claim status change that
    affects them (submitted, approved, rejected, sent back), `app/
    services/eligibility_balance_service.sync_balance` recomputes
    ApprovedAmount and InProgressAmount from scratch (a fresh SUM over
    `Childcare_ClaimMaster`/`Childcare_ClaimApprovalHistory` for that
    EligibilityID, not an incremental delta — deliberately, to avoid any
    drift from a missed edge case) and writes ApprovedAmount,
    UtilizedAmount (kept equal to ApprovedAmount — the same meaning
    "Utilized" already has in both eligibility reports, items 32/41),
    InProgressAmount, and RemainingAmount = AllottedAmount - ApprovedAmount
    back onto the row. HR's approve action now also rejects (`Invalid
    ApprovedAmountError`, HTTP 400) an amount exceeding that specific
    child+FY's current RemainingAmount, on top of the pre-existing
    invoice-amount check — read via a row-locked query
    (`get_by_id_for_update`, `WITH (UPDLOCK, ROWLOCK)` on MSSQL) so two
    concurrent approvals against the same balance can't both pass the
    check before either commits. "Remaining"/"balance" deliberately does
    not reserve against In Progress claims (consistent with the existing
    reports' convention) — only against already-Approved amounts; this is
    a scope choice, not a completed payout system: how/whether money is
    actually disbursed, carry-forward, and any interaction with In
    Progress reservations all remain unresolved per §12. The existing
    live-computed reports (items 32, 41) were left as-is rather than
    refactored to read these columns instead — both approaches now
    necessarily agree, so there was no correctness reason to touch working
    code, and the reports predate this feature. `EligibilitySummary`'s
    existing "Remaining" figure on the My Children page and the Add Child
    flow now shows real, non-zero values automatically once claims are
    approved, with no frontend change needed, since it already read
    directly from `EligibilityResponse`'s stored-column fields (it just
    displayed frozen zeros before). The HR claim-detail page's approve
    form was updated to cap and default the input to
    `min(invoice_amount, remaining_amount)` and show the remaining balance
    inline, to avoid a round-trip just to learn the same limit the backend
    enforces.
    Existing real data predates this logic (some claims were already
    Approved/Submitted before it existed, so their eligibility row's
    balance columns were still at their frozen zero/initial values) — this
    was found and, with the user's explicit go-ahead, backfilled by
    running `sync_balance` directly against the two affected real
    eligibility rows (Krishna: EligibilityID 176, 3 already-Approved
    claims totaling ₹41,140 → RemainingAmount corrected from ₹168,000 to
    ₹126,860; Ganapti: EligibilityID 1213, 1 already-Submitted claim of
    ₹12,000 → InProgressAmount corrected from ₹0 to ₹12,000). Going
    forward, every new status transition keeps itself in sync
    automatically; no scheduled/ongoing reconciliation job was built or
    is needed for that.
45. Payout carry-forward boundary (user direction 2026-09-20, resolving
    `CODEX_MASTER_INSTRUCTIONS.md` §12's previously-unresolved
    "carry-forward behavior"): unused entitlement carries forward
    month-to-month **within** a financial year, but is forfeited at the
    FY boundary — it never carries into the next financial year. Each
    financial year's payout ledger always starts with a zero opening
    balance. Verified mathematically (not just taken on faith) that this
    is consistent with the existing approval gate (item 44): since
    `EligibilityMaster.AllottedAmount` already equals the sum of that
    FY's own eligible months' entitlement, and cumulative approved is
    already capped at that total, a valid within-FY allocation always
    exists — a claim's payout schedule can never need to reach beyond its
    own financial year. See `PAYOUT_REQUIREMENTS.md` §3, §6.
46. Approved claims are terminal (user direction 2026-09-20): once a
    claim reaches `Approved` status, it can never be un-approved,
    rejected, or cancelled — no such transition exists or will be built.
    This was asked directly because the user's own draft payout spec had
    listed "claim rejected after previous approval" and "claim cancelled"
    as recalculation triggers; the user's answer removes both from scope.
    Consequence: payout recalculation is always a forward-only, additive
    replay (every Approved claim in approval-time order, plus every
    adjustment) — never something that has to unwind an earlier event.
    See `PAYOUT_REQUIREMENTS.md` §7.
47. Payout adjustments, v1 (user direction 2026-09-20): gated by the
    existing `get_current_hr_approver` dependency — the same
    `Childcare_HRApprovers` role used everywhere else, no new
    role/table. No maker-checker: one HR approver can create an
    adjustment and have it take effect immediately (no separate
    request-then-approve step). The user mentioned a future distinct
    "Admin" role that might also get this capability, but declined to
    define it now ("admin we will define later") — deferred, not
    guessed. See `PAYOUT_REQUIREMENTS.md` §8.
48. Payout audit, v1 (proposed and unopposed 2026-09-20): no dedicated
    `Childcare_PayoutAudit` table for the first cut. `Childcare_
    ClaimApprovalHistory` (existing, immutable) and the new `Childcare_
    PayoutAdjustment` (append-only, self-documenting: who/when/why/
    original/revised amounts) already answer every one of the original
    spec's 12 audit questions except "what did a given recompute change,"
    which is answerable on demand since the ledger/allocation tables are
    fully deterministic and re-derivable from those two sources at any
    time (confirmed safe given item 46: recalculation is always a
    forward-only additive replay, never an unwind). If a concrete
    auditability gap is found once this is in use, a dedicated audit
    table can be added later without disrupting the ledger/allocation
    design. See `PAYOUT_REQUIREMENTS.md` §9.
49. Payout Increment 2 — persistence (2026-09-20): `Childcare_
    PayoutMonthlyLedger` and `Childcare_PayoutAllocation` added
    (migration `8361f7a48ffe`), and `hr_service.approve_claim` now calls
    `payout_service.recalculate_payout` after every approval (reject/
    send-back do not, since a never-Approved claim never had a payout
    allocation to begin with). No `LedgerStatus`/`AllocationStatus`
    columns, no `UpdatedDate`/`UpdatedBy`, no `CreatedBy` — both tables
    are wholesale deleted and regenerated per EligibilityID on every
    recompute, so only `CreatedDate` (when this recompute ran) is
    meaningful; who triggered it is already on record via
    `ClaimApprovalHistory.ActionBy` (item 48's audit reasoning). Found and
    fixed a real type mismatch during migration (EligibilityID must be
    BIGINT, matching `Childcare_EligibilityMaster`'s actual primary key
    type, not INT — SQL Server rejected the FK otherwise). Verified
    end-to-end against real SQL Server: reproduced `PAYOUT_REQUIREMENTS.md`
    §18's exact three-claim worked example through the real API,
    including backdating `ClaimApprovalHistory.ActionDate` in the test to
    exercise cross-month spillover deterministically (payout allocation
    anchors to the real approval timestamp, so claims approved seconds
    apart in a live test run would otherwise all land in the same real
    month). With the user's go-ahead, backfilled the one real eligibility
    row with pre-existing approved claims from before this feature existed
    (Krishna, EligibilityID 176: her 3 real claims' actual
    `ClaimApprovalHistory.ActionDate` timestamps, no backdating needed,
    all landing in September 2026 since that's genuinely when they were
    approved — ₹41,140 total, matching her existing eligibility balance
    exactly).
50. Payout Increment 5 (2026-09-20), per direct user request: "for now
    trust the HR" answers the open adjustment-validation question from
    item 44's follow-up — when `Childcare_PayoutAdjustment` is eventually
    built, it will not bound or validate the adjustment amount (no guard
    against a negative closing balance, no cap) — HR is trusted
    completely, matching `PAYOUT_REQUIREMENTS.md` §8's "no maker-checker"
    stance. This is recorded now for when that table is actually built;
    adjustments themselves were not built in this increment (the user's
    message pivoted to two other, more concrete asks below).
    A new HR-only "Payout" report (`GET /hr/reports/payout`) was added,
    filterable by financial year, employee ID, and child ID — the
    Employee + Child + Financial-Year, April-through-March pivoted shape
    `PAYOUT_REQUIREMENTS.md` §9 originally proposed as a stored
    `Childcare_PayoutSummary` table. Built as a live query over
    `Childcare_PayoutMonthlyLedger` instead (same "live report, not a
    stored aggregate" pattern as every other HR report, and consistent
    with item 48's reasoning for deferring a dedicated summary table) —
    `report_service.build_payout_report` groups ledger rows by
    (EmployeeID, ChildID, FinancialYear) and spreads each row's
    `CalculatedPayoutAmount` across Apr-Mar columns. On-screen table plus
    CSV export, matching the existing convention for every other HR
    report. Only (employee, child, FY) combinations with at least one
    approved claim ever have ledger rows at all (recompute only runs on
    approval), so nothing-to-report cases are naturally excluded rather
    than shown as all-zero rows.
    Separately, the employee-facing payout view from Increments 3-4
    (per-claim schedule on the claim detail page; the child+FY monthly
    ledger reachable from the Eligibility Report's "Monthly Schedule"
    link) was judged to already satisfy "employee should have a view to
    their child payout" — rather than duplicate it with a new page, its
    discoverability was improved instead: the nav link and page heading
    were renamed from "Eligibility Report" to "Eligibility & Payout",
    with an explicit mention of the monthly-schedule drill-down added to
    the page's description.
51. Free-tier cloud hosting (user direction 2026-09-20): SmarterASP.NET
    (SQL Server, user's existing account) + a single combined Render.com
    web service for both frontend and backend, no separate Vercel/
    Cloudflare Pages hosting. `app/main.py` now conditionally mounts a
    `static/` directory (frontend build output) and serves `index.html`
    for any unmatched path, so FastAPI serves the built React app
    same-origin — this only activates when `backend/static/` exists, so
    local development (Vite dev server on :5173, calling the backend
    separately) is unaffected. A new root-level `Dockerfile` (multi-stage:
    Node build of the frontend, copied into the existing Python backend
    image) is used only for this combined deployment; `backend/
    Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml` are
    unchanged and still used for local development. Same-origin serving
    also means CORS is no longer load-bearing in production, though the
    existing `CORSMiddleware` config is left in place since it's still
    needed for local dev (frontend on :5173, backend on :8000). Object
    storage (MinIO) replacement for production, e.g. Cloudflare R2, was
    discussed but not yet decided/actioned.
52. Claim document upload limit lowered from 10 MB to 1 MB default
    (user direction 2026-09-20), anticipating a free-tier object storage
    plan (e.g. Cloudflare R2's free tier) for production once MinIO is
    replaced — see item 51. Changed `max_upload_size_mb`'s default in
    `app/core/config.py` (and `.env.example`); the limit was already
    fully config-driven (`app/services/claim_service.py`'s
    `upload_attachment`), so no new validation logic was needed. Added a
    boundary test for a file just under the limit succeeding (previously
    only the over-limit rejection was tested).
53. Mobile responsiveness fixes (user-reported 2026-09-20): the app's
    persistent mobile nav (`AppLayout.tsx`, `sm:hidden` strip with 5-7
    links) had no `flex-wrap`, so it overflowed the viewport width on
    every single page on a phone — the main culprit for "UI going beyond
    screen." The HR Reports page's tab bar (`ReportsPage.tsx`) had the
    same problem with its 4 tabs (one is "Eligibility Utilization"),
    fixed with horizontal scroll (`overflow-x-auto` + `whitespace-nowrap`
    per tab) instead of wrapping, since it's an underlined tab bar where
    multi-row wrapping would look broken. Also added defensive
    `flex-wrap` to four page-header rows that pair a title with an
    action button/badge (`ClaimsPage`, `ChildrenPage`,
    `HRClaimDetailPage`, `ClaimDetailPage`) as a precaution, even though
    only the two fixes above were confirmed overflowing. The rest of the
    app (tables, modals, forms, filter rows, stat grids) was already
    built with responsive patterns (`overflow-x-auto` on every table,
    `flex-wrap` on filter/button rows, `sm:`-prefixed grid columns) from
    earlier increments, so no other changes were needed.
