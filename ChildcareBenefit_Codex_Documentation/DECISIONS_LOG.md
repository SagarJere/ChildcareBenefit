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
54. Cross-user cache leak on sign-out (user-reported 2026-09-22):
    `AuthProvider.signOut` only removed the `['me']` query from the
    TanStack Query cache — every other query (children, claims, payout
    reports, HR queue, HR reports, ...) is keyed independently of who's
    signed in, so it survived a logout untouched. In the same browser
    tab, logging in as a different user without a full page reload could
    briefly (or longer, if a request from the outgoing session was still
    in flight) show the previous user's cached data. Fixed by having
    `signOut` call `queryClient.cancelQueries()` then `queryClient.
    clear()` — cancel first so a slow in-flight request from the
    outgoing session can't write stale data back into the cache after
    it's been cleared.
55. Claim double-approval race (user-reported 2026-09-22, live on
    production): HR reported approving a claim once but seeing its
    payout calculated twice, attributed to the free-tier DB being slow.
    Root cause: `hr_service._require_reviewable_claim` read
    `ClaimStatus` with a plain, unlocked `SELECT` before either the
    status check or the write — two concurrent approve requests for the
    *same* claim (a slow request plus a retry/double-click) could both
    read "Submitted" before either committed, and both proceed: two
    `ClaimApprovalHistory` "Approved" rows, and `payout_service.
    recalculate_payout` (which sources approved claims from that history
    table) counted the claim's amount twice. Fixed by adding
    `claim_repository.get_claim_by_id_for_update` (row-locked) and using
    it in `_require_reviewable_claim`, so a second concurrent
    approve/reject/send-back blocks until the first commits, then
    correctly sees the already-changed status and is rejected.

    While building this, discovered a much bigger problem: SQLAlchemy's
    `.with_for_update()` silently generates *no lock hint at all* on the
    mssql dialect (verified empirically — compiling the statement shows
    a plain `SELECT`, and a two-session test confirmed a second session
    acquired the "locked" row in 0.03s instead of blocking). This means
    `eligibility_repository.get_by_id_for_update` — the item-44 lock
    that was supposed to prevent concurrent approvals from over-spending
    a child's balance — had *never* actually been locking anything since
    it was written. Both repository functions were fixed to use
    `.with_hint(Model, "WITH (UPDLOCK, ROWLOCK)", "mssql")` instead,
    which a diagnostic script confirmed genuinely blocks (5s+ wait for
    the second session, matching the timeout). Added
    `tests/test_hr_concurrency.py`, a true two-connection/two-thread
    test (the shared, single-connection `db_session` fixture every other
    test uses can't exercise real row locking) — confirmed it fails
    without the fix and passes with it.

    Checked production for existing damage from this: found exactly one
    corrupted claim (ClaimID 4, approved twice 32 seconds apart on
    2026-09-21 — the user's actual incident), inflating its eligibility's
    Utilized/Approved amount and September payout ledger entry from
    ₹12,000 to ₹24,000. Repaired directly against the SmarterASP
    database (with explicit user confirmation first): deleted the
    duplicate `ClaimApprovalHistory` row, then re-ran
    `eligibility_balance_service.sync_balance` and `payout_service.
    recalculate_payout` for that eligibility — the same functions a
    normal approval triggers — rather than hand-editing the derived
    numbers. Verified the corrected ledger afterward. No other claim in
    the database had this defect.
56. Amount silently altered by mouse-wheel scroll (user-reported
    2026-09-22): HR reported a claim entered as ₹9000 showing as
    ₹8999.98 on the approval page. Root cause: all three ₹-amount inputs
    (`RaiseClaimPage`, `ClaimDetailPage`'s edit form, and
    `HRClaimDetailPage`'s approved-amount field) are native `<input
    type="number" step="0.01">` — scrolling the mouse wheel while the
    field is focused silently changes its value by one step per tick (a
    well-known browser behavior), and nothing else in the codebase does
    any numeric transformation on these fields (confirmed by grep and
    reading every call site) — 2 accidental scroll ticks over a focused
    field is exactly the observed ₹0.02 gap. Fixed by adding
    `onWheel={(e) => e.currentTarget.blur()}` to all three inputs, so
    scrolling the page moves the page instead of the value.

    Checked production for other claims with this signature (an amount
    a few cents off a round number): only Claim 5 (Submitted, not yet
    approved) had it. Corrected its InvoiceAmount/ClaimAmount from
    8999.98 back to 9000.00 directly (with explicit user confirmation),
    then re-ran `eligibility_balance_service.sync_balance` for its
    eligibility, since InProgressAmount had been derived from the wrong
    figure (RemainingAmount is Allotted minus Approved only — see
    `eligibility_repository.update_balance` — so it was already
    unaffected).
57. Report filter usability (user direction 2026-09-22): the financial
    year and employee filters on the HR Payout, Eligibility Utilization,
    and Claims Summary reports were free-text inputs (a placeholder like
    "e.g. 2026-27", or a raw Employee ID with no lookup). Replaced with
    two new shared components: `FinancialYearSelect` (a dropdown backed
    by a new `GET /hr/financial-years` endpoint, listing every FY that
    actually has data — `Childcare_FinancialYearMaster` rows are
    get-or-created lazily, so this can't just be a generated year range)
    and `EmployeeAutocomplete` (a name/ID search dropdown, reusing the
    same public `/auth/active-employees` list the login page's
    autocomplete already uses — see item 42 — rather than adding a new
    HR-only employee-search endpoint). Typing a raw Employee ID directly
    still works in the autocomplete field; the dropdown is just a faster
    way to find one by name.
58. Claim history modal clarity (user direction 2026-09-22): user
    reported "Claim history" (`ClaimHistoryModal.tsx`, opened from the
    HR claim detail page) needed its date changed to Invoice Date and a
    link to each claim's detail page. Both were already present (the
    date shown was already `claim.invoice_date`, and "Claim #N" was
    already a link) — verified the backend mapping
    (`HRClaimSummary.invoice_date = claim.InvoiceDate`) to rule out a
    mislabeled field. Made both more explicit anyway, since the existing
    link wasn't obviously an action: the date now reads "Invoice date:
    …" instead of a bare unlabeled value, and each row has its own
    visible "View details →" link separate from the claim number text.
59. Claims Summary Report detail popup (user direction 2026-09-22,
    correcting item 58 — the actual target was HR → Reports → Claims
    Summary, not the claim history modal): the report's "Date" column
    header was renamed "Invoice Date" (the underlying value was already
    `row.invoice_date`, per item 58's finding — only the header label
    was generic), and each row now has a "View details" action opening
    a new `ClaimDetailModal` — a read-only popup (not a page
    navigation) showing the same sections as the full HR claim detail
    page (invoice, documents, eligibility, payout schedule, approval
    history) via the existing `getHRClaimDetail` endpoint, minus the
    approve/reject/send-back controls, with an "Open full claim page"
    link out to the real page for taking action.
60. Show approver's name alongside Employee ID in approval history
    (user direction 2026-09-22): the "History" section on HR's claim
    detail page (and the new `ClaimDetailModal` popup) showed only the
    raw Employee ID for who took each action. `ApprovalHistoryEntry`
    gained an `action_by_name` field, resolved via each service's
    existing employee-name-lookup pattern (`hr_service._employee_
    display_name`; added the same small helper to `claim_service.py`,
    which didn't have one). Only the HR-facing views were changed — the
    employee's own claim detail page deliberately shows "by HR"
    generically rather than naming the specific approver, which is an
    existing, intentional design choice left untouched.
61. Approval history visual redesign (user direction 2026-09-22): the
    plain bare-list "History" section (thin left border, stacked text)
    was replaced everywhere it appears (HR claim detail page,
    `ClaimDetailModal`, and the employee's own claim detail page) with a
    new shared `ApprovalHistoryTimeline` component — an icon-and-color
    coded vertical timeline (emerald check for Approved, red X for
    Rejected, amber send icon for Sent Back, matching the colors
    already used for those action buttons), action+date on one line
    instead of stacked, and remarks in a quoted, subtly-shaded block.
    Takes a `renderActor` render-prop so the HR views can show "by Name
    (EmployeeID)" (item 60) while the employee view keeps its generic
    "by HR".
62. HR Queue filters (user direction 2026-09-22): the Claim Approval
    Queue only had status tabs. Added an Employee filter (reusing
    `EmployeeAutocomplete`) and an invoice date range (from/to,
    matching the Claims Summary Report's date-filter semantics) below
    the status tabs, plus a "Clear filters" button that appears once
    any are set. Required adding `date_from`/`date_to` support to
    `GET /hr/claims` all the way down (`claim_repository.
    get_claims_for_hr` → `hr_service.list_claims` → the endpoint),
    filtering by `ClaimMaster.InvoiceDate` — this endpoint previously
    only supported status/employee_id/child_id. Also renamed its
    "Date" column to "Invoice Date" for consistency with the reports
    (item 59).
63. First-year payout, Increment 1 — calculator + schema (user direction
    2026-09-22/23): a child's first 13 months of life (month 1 = birth
    month) are now paid automatically, with no claim, per new user
    requirement; months 14-72 remain claim-driven as before. This
    increment covers only the calculation/persistence layer — not yet
    wired into add-child, claim creation, or reports (increments 2-5).

    `eligibility_calculator.py` gained `FIRST_YEAR_PAYOUT_CHILD_MONTHS =
    13` and `is_first_year_payout_month(child_dob, month)`, deliberately
    a new function rather than repurposing the existing
    `claim_requires_documents`/`DOCUMENT_FREE_CHILD_MONTHS = 12` (month
    1-12 document-optional) flag — the semantics differ (that one is an
    unenforced "recommended" flag per item 38; this one will gate a hard
    block in Increment 3) and the boundary differs by one month.

    `payout_calculator.calculate_payout_schedule` now takes `child_dob`
    and partitions each eligibility window's months into "first-year"
    (auto-paid in full, zero carry-forward interaction) and "claimable"
    (the existing claim-driven pointer/carry-forward mechanics,
    unchanged, just scoped to this sub-list). Because child age only
    increases with calendar time, first-year months are always a prefix
    of the window — never interleaved with claimable ones — so the
    claimable months always start fresh at opening balance 0 regardless
    of how many first-year months preceded them. The late-join/late-
    enrollment case (employee joins after the child is already past
    month 13) falls out for free: the intersection of "child age 1-13"
    with "the eligibility window" (which already accounts for join date)
    is simply empty, no special case needed.

    Schema: `Childcare_PayoutMonthlyLedger` gained `FirstYearPayoutAmount`
    (NOT NULL, default 0) — mutually exclusive per month with the
    existing `ClaimAllocatedAmount`. `CalculatedPayoutAmount` is now
    their sum (previously just `ClaimAllocatedAmount`).
    `Childcare_PayoutAllocation` (the per-claim table) is untouched —
    there's no claim behind a first-year month to allocate.

    Many existing integration tests use a child DOB of "2026-03-01" —
    recent enough to fall inside the new first-year window as of
    2026-09-23 — so approving a claim for them now correctly finds zero
    claimable months and raises `PayoutCapacityExceededError` (expected:
    claim-blocking for that period is Increment 3, not yet built). Fixed
    by aging up the affected tests' child DOBs to 2024-06-01 (past month
    13, still well within the 6-year cutoff) wherever the test's point is
    claim/payout mechanics unrelated to this feature. One test
    (`test_full_worked_example_persists_correctly_across_multiple_
    approvals`) specifically needed eligibility to *start* in September
    to match PAYOUT_REQUIREMENTS.md §18's worked example — re-anchored
    that via the employee's join date instead of the child's DOB, keeping
    the child itself old.
64. First-year payout, Increment 2 — add-child integration (user
    direction 2026-09-22/23): `child_service.add_child` now populates the
    payout ledger immediately via the same `payout_service.
    recalculate_payout` from Increment 1 — with zero claims at add time,
    it naturally comes out as first-year-only rows. Discovered that
    item 43's existing "always create next financial year's eligibility
    too, capped at the six-year cutoff" default already covers every
    case where the first-13-months window spans two FYs (that window is
    always shorter than the six-year one it's nested inside), so no new
    "eager next-FY creation" logic was needed — just calling the same
    ledger-population step for both eligibility records when both exist.

    Found and fixed a real problem while wiring this in: calling
    `recalculate_payout` unconditionally, even for a child with nothing
    to auto-pay (e.g. already past month 13) and no claims yet, created
    ledger rows where every amount is zero — breaking the Payout Report's
    existing assumption (its own code comment) that a child only has
    ledger rows once there's something to report. Fixed with
    `child_service._has_first_year_payout`: since first-year months are
    always a *prefix* of an eligibility window (age only increases with
    calendar time — see Increment 1), checking just the window's first
    month is enough to know whether the whole window has anything to
    auto-pay; `recalculate_payout` is now only called when it does.
    Several existing tests that build a fresh child and immediately check
    the ledger/report is empty needed the same "age the child up"
    treatment as Increment 1's fixes, for the same reason.

    New `tests/test_first_year_payout.py` covers this increment
    end-to-end: a fresh child gets first-year ledger rows immediately; a
    child whose window spans two FYs gets the split correctly on both
    eligibility records; a child with nothing to auto-pay gets no ledger
    rows at all; and the late-join override (employee joins after the
    child is already past month 13, even though the child is still young
    enough by age) correctly results in no first-year payout.
65. First-year payout, Increment 3 — claim blocking (user direction
    2026-09-22/23): `claim_service._resolve_eligibility_for_invoice`
    (shared by both `create_claim` and `update_claim`) now rejects an
    invoice date falling within the child's first 13 months with a new
    `FirstYearPayoutPeriodError` (400) — that period has no claim to
    raise, it's paid automatically. Same late-join override as
    Increments 1-2 applies here too, for the same reason (the eligibility
    window itself never reaches those months).

    Found and fixed a real bug in `is_first_year_payout_month` while
    investigating an unrelated test failure: `child_month_number` returns
    zero or negative for a date *before* the child's own birth month,
    which satisfied "<= 13" and so incorrectly counted as first-year —
    meaning a claim dated before a child was even born was being blocked
    with the wrong error (and, more importantly, would have been
    incorrectly blocked in production for any legacy/backdated invoice
    predating a child's DOB). Fixed by also requiring the month number be
    >= 1. Added a regression test.

    This increment had by far the widest test-suite blast radius of the
    three so far: dozens of existing tests across test_claims.py,
    test_hr.py, test_eligibility_balance.py, test_reports.py, and
    test_security_hardening.py used a shared "young child" DOB fixture
    (2026-03-01) purely for convenience, with no relation to age — now
    that raising a claim for a young child is a real business rule, not
    just an incidental test detail, all of them needed aging up to a DOB
    safely past month 13 (2024-06-01, consistently). One test's entire
    premise (`test_submit_claim_succeeds_without_documents_in_first_
    twelve_months`) became impossible to construct at all — a claim
    genuinely cannot exist for that period anymore — and was removed
    outright; its coverage of "submission doesn't require documents" is
    already provided by the sibling month-13+ test, since that's the only
    period a claim can exist in now. One test
    (`test_headcount_report_counts_children_correctly`) deliberately
    needed a young child for its "0-1" age-bracket assertion and was left
    untouched, since it never raises a claim.

    New tests in `tests/test_first_year_payout.py` cover the blocking
    behavior directly: create blocked at month 13, allowed at month 14,
    update blocked when moved into the first-year period, and the
    late-join override still permitting claims despite a young child.
66. First-year payout, Increment 4 — reports split (user direction
    2026-09-22/23): `report_service.build_payout_report` gained a
    `source` parameter (`"claim"` or `"first_year"`) — same grouping/
    pivot logic as before, just summing `ClaimAllocatedAmount` or
    `FirstYearPayoutAmount` instead of the combined
    `CalculatedPayoutAmount`, with (employee, child, FY) groups that have
    nothing to report for the requested source excluded (same
    "nothing-to-report isn't shown as an all-zero row" convention the
    report always had — necessary now since a ledger row can exist from
    one source with genuinely nothing from the other, e.g. a fresh
    child's first-year rows before any claim is ever approved).

    New endpoints `GET /hr/reports/payout/first-year` and `GET
    /eligibility/payout-report/first-year` (employee's own), siblings of
    the existing (now explicitly claim-only) `/hr/reports/payout` and
    `/eligibility/payout-report`. Frontend: HR → Reports gets a new
    "First Year Payout" tab (the `PayoutReport` component took a
    `source` prop rather than being duplicated); "My Payout" shows both
    as two labeled sections on one page (not tabs) per the earlier-agreed
    default, each with its own total/table/CSV export.

    Also fixed a real consistency gap found while wiring this in: the
    Home page's "Total Payout" stat card and "Monthly Payout" chart only
    ever queried claim payout — a family still in their first-13-months
    period would have seen ₹0 there despite real automatic payout. Both
    now combine both sources; HR's "Total Approved Payout" stat card was
    already correctly scoped by its own label and was left unchanged.
67. First-year payout, Increment 5 — production data wipe (user
    direction 2026-09-22/23, executed 2026-09-24 with explicit
    confirmation of scope): since the app is still in testing and none of
    the existing production data was created under the new first-year
    rule, all child/eligibility/claim/payout data on the SmarterASP
    database was deleted — `Childcare_ChildMaster`,
    `Childcare_EligibilityMaster`, `Childcare_ClaimMaster`,
    `Childcare_ClaimAttachments`, `Childcare_ClaimApprovalHistory`,
    `Childcare_PayoutMonthlyLedger`, `Childcare_PayoutAllocation` — in
    FK-safe order as one transaction, plus both objects in the Cloudflare
    R2 document bucket. `Master_Emp_BasicInfo`, `Childcare_HRApprovers`,
    and `Childcare_FinancialYearMaster` were left untouched, the same
    scope as the earlier local-dev wipe (item — see the full data wipe
    entry earlier in this log). This closes out the first-year-payout
    feature (items 63-67).
68. Duplicate add-child submission (user-reported 2026-09-24): adding one
    child on production resulted in two separate `ChildID`s ("Shivaay",
    same DOB, ~1.5 minutes apart — not a millisecond race like item 55's
    claim-approval bug, so most likely the free-tier host's cold-start
    latency made the first attempt look hung and the user resubmitted).
    The frontend already disables the submit button while the mutation
    is pending, so this wasn't a same-render double-click; the gap
    points to a genuinely separate second submission with no
    server-side duplicate guard to catch it.

    Fixed two ways: (1) `child_service.add_child` now checks the
    employee's existing active children for an exact name+DOB match
    (case/whitespace-insensitive) before inserting, raising a new
    `DuplicateChildError` (409); (2) added `Childcare_ChildMaster.
    UQ_ChildMaster_Employee_Name_DOB`, a real database-level unique
    constraint, as a backstop for a genuine concurrent-request race that
    check-then-insert alone can't close — `add_child` wraps the insert in
    a SAVEPOINT and catches the resulting `IntegrityError`, the same
    pattern `financial_year_repository.get_or_create` already uses. Not
    filtered on `IsActive` since child deactivation isn't implemented.

    Both existing duplicate "Shivaay" records (and their full first-year
    payout ledgers — each had its own complete, independent eligibility
    and 20 ledger rows, so the employee was seeing double their correct
    payout total) were removed as part of a second full production wipe
    at the user's request ("clear everything except employee and HR
    data... I test again"), since the new unique constraint couldn't be
    added while the violating duplicate still existed. Same scope as
    items 67/the earlier wipe.
69. First-year payout was never counted as utilized anywhere (user-caught
    2026-09-23 with "Isnt first year payout will be utilised amount.?").
    `child_service.add_child` populated `Childcare_PayoutMonthlyLedger`
    with first-year auto-pay rows (items 63-64) but never called
    `eligibility_balance_service.sync_balance` afterward, and even where
    `sync_balance` *is* called elsewhere, it only ever summed claim-
    approved amounts — so `EligibilityMaster.UtilizedAmount`/
    `RemainingAmount` stayed at their initial (no-payout-yet) values
    despite real money already having been auto-paid. Practical risk: HR
    could approve a claim up to the inflated `RemainingAmount`, exceeding
    the payout calculator's true remaining *claimable* capacity (first-
    year months are removed from that pool entirely — see
    `payout_calculator.py`), which would then raise
    `PayoutCapacityExceededError` instead of being caught by HR's normal
    balance-cap check.

    Fixed in three places, all following the same rule — "utilized" and
    "remaining" must account for claim-approved *and* first-year auto-
    paid amounts, not claim-approved alone:
    - `payout_repository.get_first_year_payout_totals` (new, batched —
      matches `get_approved_totals_by_eligibility`'s convention): sums
      `FirstYearPayoutAmount` per `EligibilityID`.
    - `eligibility_repository.update_balance` now takes
      `first_year_payout_amount` and folds it into `UtilizedAmount`
      (`ApprovedAmount` stays claim-approved only) and `RemainingAmount`;
      `eligibility_balance_service.sync_balance` fetches and passes it;
      `child_service.add_child` now calls `sync_balance` right after each
      `recalculate_payout` call (current- and next-FY branches both).
    - The two live-computed reports that are supposed to agree with the
      stored columns "by construction" (item 32's comment) had the
      identical bug independently: `report_service.
      build_eligibility_utilization` (`remaining_after_approved`) and
      `build_employee_eligibility_report` (`utilized_amount`/
      `balance_amount`) both now also subtract/include first-year payout
      totals, fetched the same batched way.

    Verified with the project's standard revert/restore methodology
    (write the test, confirm it fails against the un-fixed code, restore
    the fix, confirm it passes) for all four fixes — see
    `test_first_year_payout.py`'s
    `test_add_child_with_first_year_payout_updates_eligibility_balance`,
    `test_hr_approval_cap_accounts_for_first_year_payout_already_consumed`,
    `test_hr_eligibility_utilization_report_accounts_for_first_year_payout`,
    and `test_employee_eligibility_report_accounts_for_first_year_payout`.
    No production data repair needed — production had just been fully
    wiped (item 68) with no children added since.
70. First-year payout catch-up on late add-child (user direction
    2026-09-24): "payout should start from the month in which we added
    the Child details, the previous month carry-fwd logic should apply
    here as well... if Child DOB in Aug 26 and we added the details in
    Sep 26 then Sep 26 should have 14k + 14k and rest remains as it is."
    Previously every first-year month got its own standalone 14,000 row
    regardless of when the child was actually entered into the system —
    a child added several months after birth would show payout amounts
    against months before the record even existed, which doesn't match
    any real disbursement.

    `payout_calculator.calculate_payout_schedule` gained a required
    `first_year_payout_as_of_date` parameter and a new
    `_first_year_payout_by_month` helper: every first-year month up to
    and including the one containing that date is bundled into that one
    month's `first_year_payout_amount` (earlier ones become 0); every
    first-year month after it is untouched at its own standalone 14,000.
    This is the same "catch-up" shape as the claim-driven pointer
    mechanic just above it in the same function, but anchored to one
    fixed event (the record's creation) instead of a list of claim
    approvals, so it always resolves to exactly one bundling point.

    The as-of date has to be a stored fact, not `date.today()` re-read on
    every `recalculate_payout` call (which happens again on later claim
    approvals for the same eligibility) — otherwise the bundling point
    would silently drift forward each time. Added
    `Childcare_EligibilityMaster.FirstYearPayoutAsOfDate` (nullable —
    existing rows fall back to `EligibilityStartDate`, i.e. no catch-up,
    preserving their original behavior), set once to `date.today()` in
    `child_service.add_child` for both the current- and next-FY
    eligibility records it creates. Using the same value for both is
    deliberately uniform rather than special-cased: for the current-FY
    record the add date normally falls inside the window (triggering
    catch-up), while for the next-FY record it normally falls *before*
    the window even starts, which the same bundling formula naturally
    resolves to "no catch-up" — by the time next year's window opens,
    the record has existed for a full financial year already, so nothing
    was ever missed.

    Verified with the project's standard revert/restore methodology.
    New coverage: `test_payout_calculator.py`'s
    `TestFirstYearPayoutCatchUp` (pure calculator math — one month late,
    several months late, added before the window starts, and that
    claim-driven months are unaffected). One existing integration test,
    `test_add_child_splits_first_year_payout_across_two_financial_years`,
    had its per-row assertion loosened to an aggregate total, since which
    row receives the bundle now depends on "today" (the exact math is
    already covered by the new calculator-level tests).
71. Claim now captures Institution Name and a From Date/To Date service
    period (user direction 2026-09-24). Confirmed with the user before
    building: From Date must fall at/after the child's 14th month (no
    claim needed before that — first-year payout covers it); To Date
    must fall at/before the child's 72nd month (the same six-year
    eligibility cutoff); both are descriptive-only — they don't change
    which EligibilityID a claim posts against (still InvoiceDate) or
    payout allocation (still HR approval time), and the two dates are
    explicitly allowed to span two financial years, since they're not
    tied to any single eligibility window. Institution Name is required,
    capped at 200 characters (no specific limit requested — used the
    project's standard "name field" length).

    Backend: `Childcare_ClaimMaster.InstitutionName/FromDate/ToDate`
    (migration `f1a4c8d9e623`, nullable — legacy claims keep working
    with nulls); `eligibility_calculator.is_valid_claim_from_date`/
    `is_valid_claim_to_date` (new pure helpers, `MIN_CLAIMABLE_CHILD_
    MONTH`/`MAX_CLAIMABLE_CHILD_MONTH` constants); `claim_service.
    _validate_service_period` (new `InvalidServicePeriodError` → 400),
    checked after the existing first-year-payout/eligibility checks so a
    claim blocked for an earlier reason still gets that specific error.
    `ClaimCreateRequest`/`ClaimUpdateRequest` also validate From Date <=
    To Date at the schema level (no child context needed for that part).
    Surfaced in every claim-facing schema that mirrors `ClaimResponse`:
    `HRClaimSummary`/`HRClaimDetail` and the Claims Summary report's
    `ClaimSummaryRow`.

    Frontend: added to the Raise Claim form and the editable claim-detail
    form (`claimSchema.ts` validates required + From<=To; the 14/72-month
    age bounds are left to the backend's error message, not duplicated
    client-side, since the form doesn't otherwise have easy access to
    calculator logic); shown read-only on the employee and HR claim
    detail views/modal; added an Institution column to the HR Claims
    Summary report (From/To Date were left out of that already-wide
    table but do flow through its CSV export, which dumps every field).

    Caught mid-testing: `test_hr_concurrency.py` builds a claim via a
    direct `ClaimCreateRequest(...)` call rather than a JSON payload, so
    it was missed by the bulk fix-up of ~56 other claim-creation test
    payloads and started failing validation — its `setup_session` was
    then never closed on that failure (a pre-existing gap, not new),
    leaving an orphaned open transaction on the local dev SQL Server that
    silently blocked the next run's use of the same rows for several
    minutes before being tracked down via `sys.dm_exec_requests`/
    `sys.dm_exec_sessions` and killed. Fixed both: added the missing
    fields to that test, and added `setup_session.close()` to the test's
    cleanup `finally` so a future failure there can't leak a session
    again.

    Verified: full backend suite (178 passed, only the pre-existing
    MinIO-dependent tests excluded), ruff/mypy clean; frontend `tsc
    --noEmit`, `oxlint`, and `vite build` all clean. The new fields'
    read path was also checked against real local dev data (an existing
    pre-feature claim correctly shows `institution_name`/`from_date`/
    `to_date` as `null` rather than breaking). The UI itself was not
    visually exercised in a browser — no browser-automation tool was
    available in this environment to do so.
