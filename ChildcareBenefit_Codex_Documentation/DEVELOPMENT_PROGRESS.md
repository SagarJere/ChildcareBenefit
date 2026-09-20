# Development Progress

## Confirmed
- ₹14,000 monthly benefit
- Maximum 2 children
- April-March FY
- Join date and child DOB eligibility rules
- Automatic eligibility when child is added
- ChildID EmployeeId_1 / EmployeeId_2
- First 12 months no bills
- Month 13 onward documents recommended (informational only, not enforced
  — see 2026-09-19 post-Increment-7 improvements below)
- Employee claims
- Receipt/invoice + payment proof
- HR Approve/Reject/Send Back
- HR approved amount
- Existing employee master
- React + Vite
- FastAPI
- SQL Server
- MinIO
- Production-ready quality requirement

## Pending
- Exact payout calculation
- Carry-forward rules
- Monthly payout semantics
- Production authentication provider
- HR role source
- Deployment environment
- Document retention

## Corrected
- `Master_Emp_BasicInfo` real schema (confirmed 2026-09-19 against the
  local `ChildcareBenefit` database): `MEmpID`, `EmployeeID`, `FullName`,
  `MySingleID`, `Joindate`, `IsActive`. No `Gender` column exists, and the
  active flag is `IsActive = 1` (not `Inactive = 0`). All columns are
  nullable. `DATABASE_DESIGN.md`, `LOGIN_REQUIREMENTS.md`,
  `BUSINESS_RULES.md`, and `CODEX_MASTER_INSTRUCTIONS.md` were updated to
  match; see `DECISIONS_LOG.md` items 9-10.

## Completed
- Increment 1 — Project Foundation implementation completed on 2026-09-19.
  (Note: an earlier version of this document recorded this increment as
  completed on 2026-09-17, but no project code existed in the repository
  at the start of this session — only this documentation folder. That
  entry was inaccurate and has been corrected here.)
- Created a React + Vite + TypeScript frontend foundation (`frontend/`)
  with Tailwind CSS v4, React Router, Axios, TanStack Query, React Hook
  Form, Zod, Lucide React, and Sonner, plus a minimal home screen that
  calls the backend health endpoint and shows loading/error/success
  states. Verified with `npm run build` and `npm run lint` (Oxlint).
- Created a FastAPI foundation (`backend/`) with layered structure
  (api/core/database/dependencies/models/repositories/schemas/services),
  environment-variable-based settings (`app/core/config.py`), structured
  JSON logging with request correlation IDs, centralized exception
  handling with safe error responses, restricted/configurable CORS, and
  `GET /api/v1/health`.
- Added a lazy SQL Server SQLAlchemy engine/session (`app/database/`) that
  only connects on first use, and an Alembic migration setup
  (`backend/alembic.ini`, `database/migrations/`) with a single empty
  baseline revision; no business tables were created.
- Added a server-only MinIO service abstraction
  (`app/services/storage/minio_client.py`) and environment-based private
  bucket configuration; no document upload endpoint or credential exposure
  to the frontend was implemented.
- Added `.env.example` files (root, backend, frontend), `.gitignore`
  rules, Dockerfiles for both apps plus a root `docker-compose.yml`
  (backend, frontend, local SQL Server and MinIO containers for dev), and
  a root `README.md` with local run/test instructions.
- Backend tests: 8 automated tests (`backend/tests/`) covering the health
  endpoint (including that it responds without a configured database) and
  the configuration foundation (CORS origin parsing, SQL Server URI
  construction, log level validation). All 8 pass under Python 3.14 in a
  fresh virtual environment; `ruff check .` and `mypy app` both pass clean.
- Verified end-to-end locally: started the backend with `uvicorn`, hit
  `GET /api/v1/health` directly (200 OK), started the frontend with
  `npm run dev`, and confirmed in a real headless-browser render that the
  home page successfully calls the backend and displays
  "Childcare Benefit API is ok (development)".
- Verified `alembic history`/`alembic heads` read the baseline revision
  correctly, and that `alembic upgrade head` fails with a clear, safe
  error message (not a stack trace) when SQL Server is not configured.
- Connected the backend to the user's local SQL Server instance
  (`ChildcareBenefit` database) using the app's real configuration and
  SQLAlchemy engine, confirming `Master_Emp_BasicInfo` exists (0 rows).
  Added `MSSQL_AUTH_MODE` (`sql`/`windows`) support and made `MSSQL_PORT`
  optional to support this local Windows-Authentication, shared-memory
  connection; added 5 new config tests (12 total) and fixed a test
  isolation gap where a developer's local `.env` could affect config unit
  tests. All 12 backend tests, `ruff`, and `mypy` still pass.

- Increment 2 — Employee Login completed on 2026-09-19, following the
  sequence in `CODEX_MASTER_INSTRUCTIONS.md` §6: receive Employee ID,
  query `Master_Emp_BasicInfo`, verify exists, verify `IsActive = 1`,
  return employee details.
  - Backend: `POST /api/v1/auth/login` (Employee ID in, a signed JWT
    access token + `EmployeeProfile` out) and `GET /api/v1/me` (returns
    the current employee, re-read from the database on every call — never
    trusted from the token beyond identity). A single generic
    "Employee ID not found or not active." message is used for both the
    unknown- and inactive-employee cases so the endpoint can't be used to
    enumerate valid IDs.
  - `app/models/employee.py` maps the real `Master_Emp_BasicInfo` table
    read-only (no Alembic migration touches it); `MEmpID` is declared
    `autoincrement=False` since it is verified not to be a SQL Server
    identity column.
  - `app/core/security.py` issues/verifies JWTs (`JWT_SECRET_KEY`,
    `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`); no default secret is baked
    in, so login/`.../me` fail with a clear, safe error until it's set.
  - Fixed `HTTPBearer`'s default 403-on-missing-token behavior to return
    401 instead, for consistency with `ERROR_HANDLING_AND_LOGGING.md`.
  - Frontend: `/login` page (React Hook Form + Zod), an `AuthProvider`
    (`src/features/auth/`) that persists the token in `localStorage` and
    revalidates it via `/me` on load (via TanStack Query, not a manual
    effect), a `ProtectedRoute` guarding the home screen, sign-out, and an
    Axios interceptor that clears the session on any `401` other than a
    failed login attempt.
  - Tests: 9 new backend integration tests (`backend/tests/test_auth.py`)
    run against the real local `Master_Emp_BasicInfo` table inside a
    transaction that is always rolled back (nothing persists), covering
    unknown/inactive/null-active employees, successful login, `/me` with
    no/garbage/valid tokens, and a token becoming invalid mid-session when
    the employee is deactivated. Plus 5 new JWT unit tests
    (`test_security.py`). 26 backend tests total, all passing;
    `ruff`/`mypy` clean. Frontend: `npm run build` and `npm run lint`
    clean.
  - Verified end-to-end with a real (temporary, cleaned-up-after) employee
    row: manual `curl` login/`/me` flow, and a full headless-browser run
    of login → protected home → page reload (session persists) → sign out
    → redirected to `/login`.
  - Assumption made without a business-rule impact: failed-login and
    missing-token responses are `401` (not `403`/`404`), matching REST
    convention and this project's own `ERROR_HANDLING_AND_LOGGING.md`.

- Increment 3 — Child Management + Eligibility completed on 2026-09-19,
  implemented as the single atomic operation required by
  `CODEX_MASTER_INSTRUCTIONS.md` §8 (validate → generate ChildID → create
  child → calculate eligibility → create eligibility record, one
  transaction, rolled back on any failure).
  - Database: Alembic migration adds `Childcare_FinancialYearMaster`,
    `Childcare_ChildMaster`, `Childcare_EligibilityMaster` (applied to the
    user's local database). `MEmpID` columns are plain indexed `INT`, not
    foreign keys, since `Master_Emp_BasicInfo` has no PK/unique constraint
    to reference (see `DECISIONS_LOG.md` item 14).
  - Eligibility math lives in one pure, dependency-free module
    (`app/services/eligibility_calculator.py`) per §8's "must not be
    duplicated across multiple endpoints" — financial year computation,
    the latest-of-three-months start rule, and the six-year cutoff are all
    there, with 13 unit tests covering each rule and edge cases (leap-day
    DOB, employee already aged the child out, joining mid-year, etc.).
  - Six-year cutoff confirmed by user 2026-09-19 (see `BUSINESS_RULES.md`
    and `DECISIONS_LOG.md` item 12): last eligible month is the month
    containing the 6th birthday, paid in full.
  - Backend endpoints: `POST /api/v1/children` (atomic create, 201),
    `POST /api/v1/children/preview-eligibility` (same calculation,
    read-only — needed for `UI_UX_REQUIREMENTS.md`'s "eligibility preview
    before save" and not in the original `API_SPECIFICATION.md` list),
    `GET /api/v1/children`, `GET /api/v1/children/{childId}`,
    `GET /api/v1/eligibility`, `GET /api/v1/eligibility/{childId}`. `PUT
    /children/{childId}` (edit) is intentionally not implemented — editing
    a child's DOB would require re-running eligibility, which is new
    unresolved scope, not part of "adding a child".
  - Ownership is enforced entirely from the JWT-derived employee, never
    from any client-supplied ID — verified by a test that a second
    employee cannot see or fetch the first employee's child.
  - Frontend: "My Children" page (responsive cards: name, DOB, computed
    age, eligibility summary) and "Add Child" (React Hook Form + Zod,
    live eligibility preview via TanStack Query as the DOB is typed,
    submits only on confirm). The "Add Child" button hides once two
    children exist, but the backend independently rejects a third
    regardless — verified by navigating to the form directly.
  - Two real bugs found and fixed by testing against real SQL Server
    (not a mock): `SQLAlchemy`'s `.is_(True)` compiles to invalid T-SQL
    (`IS 1`) for a BIT column — changed to `== True`; the custom
    validation-error handler wasn't sanitizing Pydantic's error `ctx`
    field (can hold a raw exception object) before JSON-encoding it,
    causing a 500 instead of the intended 422 for `child_dob`
    validation — fixed with `jsonable_encoder`.
  - Also fixed a real transaction-safety bug written earlier in this same
    increment: the financial-year get-or-create's conflict handling called
    `db.rollback()`, which would have discarded the *entire* request's
    transaction (not just that insert) — changed to a SAVEPOINT
    (`db.begin_nested()`).
  - Tests: 13 new integration tests (`test_children.py`, real DB,
    transaction rolled back after each) plus the 13 pure calculator unit
    tests — 52 backend tests total, all passing; `ruff`/`mypy` clean.
    Frontend `build`/`lint` clean.
  - Verified end-to-end in a real browser against the real database
    (temporary employee + children, cleaned up after): login → empty
    "My Children" → add child with live preview matching the documented
    UI fields exactly → card shows correct name/DOB/age/eligibility → add
    a second child → "Add Child" button disappears → direct navigation to
    the add-child form for a third child is still rejected by the backend
    with a clear, safe error.

- Increment 4 — Claims + Document Upload completed on 2026-09-19.
  - Two business-rule clarifications confirmed by user before building:
    "child month" for the months 1-12 (no bills) / 13+ (bills required)
    rule is counted from the child's **date of birth**, not from when
    benefit eligibility began (see `DECISIONS_LOG.md` item 17) — a child
    enrolled late can already be past month 12 on their first claim. And
    since no MinIO instance was available and Docker isn't installed in
    this environment, the user is installing MinIO themselves and will
    provide connection details (item 21).
  - Database: migration adds `Childcare_ClaimMaster` and `Childcare_
    ClaimAttachments`. `ClaimStatus`'s CHECK constraint lists the full
    Draft→Submitted→HRReview→Approved/Rejected/SentBack domain now (this
    increment only ever sets Draft/Submitted) so Increment 5 (HR
    workflow) doesn't need a follow-up migration just to widen it.
  - Backend endpoints: `POST/GET/PUT /claims`, `GET /claims/{id}`,
    `POST /claims/{id}/submit`, `POST/GET /claims/{id}/attachments`, and
    `GET /claims/{id}/attachments/{attachmentId}/download` (added beyond
    `API_SPECIFICATION.md`'s literal list — `MINIO_DOCUMENT_STORAGE.md`
    requires authorized access to the actual file via "a short-lived
    pre-signed URL or streaming the file", which needs an endpoint; see
    `DECISIONS_LOG.md` item 23). Download returns a 307 redirect to a
    5-minute pre-signed MinIO URL rather than proxying the file.
  - `ClaimMaster.ClaimAmount` mirrors `InvoiceAmount` at creation — the
    employee isn't asked for a separate claim amount per §9's field list
    (item 18). A claim's `EligibilityID` is resolved by matching the
    invoice date to its financial year, not "the child's current
    eligibility" (item 19); a claim dated outside any FY the child has an
    eligibility record for is rejected with a clear error. Nothing in
    this increment reads or writes `Childcare_EligibilityMaster`'s
    Utilized/Approved/InProgress/RemainingAmount — §12 explicitly forbids
    guessing that mechanics (item 20).
  - `PUT /children/{childId}` is still not implemented (unchanged from
    Increment 3), but `PUT /claims/{claimId}` is — editing a claim's own
    invoice details doesn't cascade into recalculating anything else, so
    it doesn't carry the same complexity that made child-editing
    out-of-scope.
  - Frontend: a 5-step guided "Raise Claim" flow (select child → invoice
    details → upload documents → eligibility preview → review & submit)
    matching `UI_UX_REQUIREMENTS.md` exactly, plus a "My Claims" table
    with status badges. Editing an existing Draft via the UI (as opposed
    to raising a new claim) was not built — out of scope for this pass.
  - Two real bugs found by testing against the real database (not
    mocks): SQLAlchemy's `.is_(True)` compiles to invalid T-SQL (`IS 1`)
    for a BIT column on the MSSQL dialect — fixed to `== True`. The
    custom validation-error handler wasn't sanitizing Pydantic's error
    `ctx` field (can hold a raw exception object) before JSON-encoding
    it, turning a bad `child_dob` into a 500 instead of the intended 422
    — fixed with `jsonable_encoder`, the same way FastAPI's own default
    handler does it.
  - Tests: 12 new integration tests (`test_claims.py`, real DB,
    transaction rolled back after each — required-document gating is
    tested by inserting attachment rows directly, so it's covered without
    needing real MinIO) plus 6 new pure unit tests for the child-month
    rule. 71 backend tests total: 70 passing, 1 skipped (the real-MinIO
    upload/download round trip, until the user's MinIO instance is
    ready). `ruff`/`mypy` clean. Frontend `build`/`lint` clean.
  - Verified end-to-end in a real browser against the real database
    (temporary employee + two children, cleaned up after): a month-1-12
    claim goes through all 5 steps with no documents required and reaches
    "Submitted" in My Claims; a month-13+ claim correctly shows the
    document requirement and, when MinIO upload is attempted, fails with
    a clear "Document storage is not configured" toast rather than
    crashing or silently succeeding.

- MinIO configured and verified for real on 2026-09-19 (same day). MinIO's
  official binary distribution was discontinued between Increment 1 and
  this point (upstream reality, not a project decision — see
  `DECISIONS_LOG.md` item 24); the last available Windows release was
  retrieved from the Internet Archive and is running locally at
  `.minio/` (gitignored; see `README.md` for start/stop instructions).
  `backend/.env`'s `MINIO_*` now point at it. The previously-skipped
  `test_upload_and_download_attachment_with_real_minio` now passes for
  real — **71/71 backend tests pass, 0 skipped.** Verified end-to-end in
  a real browser too: a month-13+ claim's two document uploads were
  confirmed to actually land in the MinIO bucket (`client.list_objects`),
  matching the exact `claims/{EmployeeId}/{ChildID}/{ClaimID}/{UUID}-
  {name}` object key format from `MINIO_DOCUMENT_STORAGE.md`; all test
  objects and database rows were cleaned up afterward.

- Increment 5 — HR Approval Workflow completed on 2026-09-19.
  - User direction confirmed the previously-blocking gap (no document
    specified how the backend recognizes an HR approver): a dedicated
    `Childcare_HRApprovers` table (`EmployeeID`, `IsActive`) — see
    `DECISIONS_LOG.md` item 25. It starts empty; no HR approver is seeded.
  - Database: migration adds `Childcare_HRApprovers` and
    `Childcare_ClaimApprovalHistory`.
  - Backend: `get_current_hr_approver` dependency (composes with ordinary
    employee auth, then checks the new table) gates every `/hr/*`
    endpoint — `GET /hr/claims` (optional `?status=`), `GET /hr/claims/
    {claimId}` (employee + child + eligibility + documents + history in
    one response), `POST .../approve` (amount ≤ invoice, validated),
    `.../reject` and `.../send-back` (remarks required), plus HR-scoped
    attachment list/download endpoints.
  - Fixed a real gap while building Send Back: the employee-side edit/
    submit endpoints only accepted `Draft` claims, which would have made
    "Sent Back claims can be corrected and resubmitted"
    (`CODEX_MASTER_INSTRUCTIONS.md` §9) impossible. They now also accept
    `SentBack` (item 27).
  - `EmployeeProfile` (returned by login and `/me`) now carries an
    `is_hr_approver` flag, purely for frontend UX (showing/hiding the HR
    nav link) — the backend authorization check is entirely independent
    of this flag and cannot be bypassed by it.
  - As in Increment 4, this increment does not touch `Childcare_
    EligibilityMaster`'s Utilized/Approved/InProgress/RemainingAmount —
    approving a claim only records the HR-entered amount in `Childcare_
    ClaimApprovalHistory` (item 26); how that rolls up into eligibility
    balances is payout territory (§12), still unresolved.
  - Frontend: a Claim Approval Queue (status tabs: Submitted/Approved/
    Rejected/Sent Back/All) and a review screen showing everything in one
    place with Approve/Reject/Send Back actions. A client-side `HRRoute`
    guard hides the HR nav link and redirects non-HR employees away — UX
    only; the backend enforces access independently either way.
  - Tests: 12 new HR integration tests plus 2 new auth tests for the
    `is_hr_approver` flag — 85 backend tests total, all passing;
    `ruff`/`mypy` clean. Frontend `build`/`lint` clean.
  - Verified end-to-end in a real browser with two temporary employees
    (a claimant and an HR approver) against the real database: HR nav
    link correctly hidden for the regular employee and shown for the HR
    approver; queue showed the submitted claim; approval recorded the
    exact amount and remarks entered. Along the way, confirmed the queue
    also correctly showed the user's own real, unrelated pending claim
    (₹25,000, child "Krishna") without my test script touching it — and
    discovered the user had already granted a second real employee
    ("Satish G") HR access directly in the database, which was left
    untouched.

- Increment 6 — Reports completed on 2026-09-19. Scope was almost
  entirely unspecified (`FRONTEND_ARCHITECTURE.md` names "Reports" as an
  HR screen; no API spec, data, filters, or format were defined anywhere)
  — the user was asked directly rather than guessed, and confirmed all
  three report types with on-screen tables + CSV export
  (`DECISIONS_LOG.md` item 31).
  - **Claims Summary**: filterable by invoice date range, status,
    employee; totals include count-by-status and total invoice/approved
    amounts.
  - **Eligibility Utilization**: per-child Allotted / In Progress /
    Approved / "Remaining after approved" — all computed live from
    `Childcare_ClaimMaster` and `Childcare_ClaimApprovalHistory`, never
    from `Childcare_EligibilityMaster`'s own balance columns (which this
    application never updates — item 32). Deliberately does not compute
    a single balance that also subtracts in-progress claims, since that
    would require guessing the still-unresolved payout interaction rules
    (§12).
  - **Headcount**: employees with children, total children, 1-vs-2-child
    breakdown, children by original enrollment financial year (item 34)
    and by age bracket.
  - All three gated by the same `get_current_hr_approver` dependency as
    Increment 5 (item 33). CSV export is real CSV (opens natively in
    Excel), not a generated `.xlsx` — no extra dependency needed.
  - A real FastAPI startup bug was caught immediately by the test suite:
    a `Union[PydanticModel, Response]` return type isn't valid for
    FastAPI's automatic response-model generation and crashes at route
    registration — fixed with `response_model=None` on all three report
    routes.
  - Tests: 6 new report tests (live-computed totals verified against
    actual approve/submit flows, CSV content-type and header checks,
    non-HR 403) — 91 backend tests total, all passing; `ruff`/`mypy`
    clean. Frontend `build`/`lint` clean.
  - Verified end-to-end in a real browser with temporary employees and a
    real approval: all three report tabs, filters, and CSV downloads
    confirmed working against the real database — including catching
    that an early verification script's screenshots looked identical
    across tabs (a test-script timing artifact) and confirming via a
    targeted follow-up that the tabs and computed figures were correct
    all along.

- Increment 7 — Security & Performance Testing completed on 2026-09-19.
  Scoped directly from `SECURITY.md`'s existing checklist (no clarifying
  question needed, unlike Reports — item 35).
  - Systematic audit, all clean: no hardcoded secrets anywhere in
    `app/`; every database query goes through the ORM's parameterized
    `select()` (no raw/f-string SQL); CORS restricted to configured
    origins only (no wildcard); no logging of passwords, tokens,
    document contents, or request bodies; every route other than
    `/auth/login` and `/health` carries the correct authorization
    dependency (cross-checked by counting `@router` decorators against
    `Depends(get_current_employee/hr_approver)` usages, per file).
  - Found and fixed a real N+1 query pattern in `hr_service.list_claims`
    (child + employee-name lookups were per-claim, not batched) — this
    mattered specifically because the HR queue scales with claims across
    *all* employees, unlike an employee's own bounded claims list (item
    37). A query-count regression test now locks the fix in.
  - New tests (8, all passing): path traversal in an uploaded filename
    can't escape its storage prefix; an expired JWT is rejected; HR
    access revoked mid-session is rejected on the very next request (not
    just at next login); an employee cannot download or even see another
    employee's claim/attachments (404, not 403 — doesn't confirm the
    claim exists); a SQL-injection-shaped filter value returns an empty
    result, not an error; CORS headers are present only for the
    configured origin. 99 backend tests total, all passing; `ruff`/`mypy`
    clean.
  - Found and fixed a real test-hygiene gap while investigating a 30-object
    MinIO bucket that should have had 2: `test_hr.py`'s attachment test
    was leaking a real MinIO upload on every run (28 stray objects
    accumulated across this session) because it lacked the same
    real-upload cleanup already used elsewhere — fixed and verified the
    bucket stays at exactly the user's own 2 real files across repeated
    full-suite runs.
  - Two `SECURITY.md`/`DEPLOYMENT.md` items are explicitly out of this
    application's code to provide — a least-privilege SQL Server login
    and HTTPS/TLS termination — both require actual infrastructure
    provisioning by whoever operates the production environment (item
    36), not something to fake in code.

- Post-Increment-7 validation improvements completed on 2026-09-19, per
  direct user request (three related small changes, not a numbered
  roadmap increment):
  1. The child-month-13+ document-upload requirement is no longer
     enforced as a submission blocker — `claim_service.submit_claim` no
     longer raises on missing documents, and the now-dead
     `MissingRequiredDocumentsError` was removed rather than left unused.
     `requires_documents` is still computed and shown to both the
     employee (Raise Claim step 3) and HR (claim detail page) as
     guidance only. See `DECISIONS_LOG.md` item 38.
  2. Claim creation and editing now reject a duplicate invoice number for
     the same employee + child, across claims of any status
     (`claim_repository.get_by_invoice`, `DuplicateInvoiceError` -> HTTP
     409). See `DECISIONS_LOG.md` item 39.
  3. Added an optional `Comments` field an employee can fill in while
     raising a claim (migration `b6e682ad8a0d` adds a nullable
     `Comments` column to `Childcare_ClaimMaster`), shown read-only to HR
     on the claim detail page. See `DECISIONS_LOG.md` item 40.
  - Also relaxed the HR claim-detail page's Approve button, which
    previously disabled Approve when documents were missing — that gate
    only ever existed in the frontend (the backend never enforced it),
    but leaving it in place after (1) would have made month-13+ claims
    submitted without documents permanently unapprovable. The "missing
    document" note is kept as informational text.
  - Fixed a real, unrelated test bug surfaced while re-running the full
    suite: `test_hr.py::test_hr_list_filters_by_status` asserted zero
    `Approved` claims exist anywhere in the (intentionally unscoped)
    real database — no longer true since the user has genuinely approved
    a real claim through the live app. Fixed to check only that this
    test's own claim is correctly excluded from the `Approved` filter.
  - Tests: 6 new/updated claim tests (duplicate-invoice on create/update,
    comments round-trip, month-13+ submission without documents now
    succeeds) plus the `test_hr.py` fix — 104 backend tests total, all
    passing; `ruff`/`mypy` clean. Frontend `build`/`lint` clean.
  - Applied the new migration and verified against the real database and
    the running dev servers (backend restarted to pick up the code
    change; frontend picked it up via Vite HMR).

- Further post-Increment-7 improvements completed on 2026-09-19, per
  direct user request:
  - Employees can now edit/continue a Draft claim and view, correct, and
    resubmit a SentBack claim (new `ClaimDetailPage.tsx` at
    `/claims/:claimId`, linked from "My Claims" as "Continue"/"View").
    The backend already allowed this (`_get_owned_editable_claim` covers
    Draft and SentBack); the gap was purely that no frontend page existed
    to reach it. `ClaimResponse` now also includes `approval_history` (a
    new shared `app/schemas/approval_history.py`, split out of the
    HR-only `app/schemas/hr.py`) so employees can see HR's remarks and
    the full action history on their own claim — a SentBack banner
    surfaces the latest remark up top.
  - Added a kid-wise, financial-year-wise eligibility report for
    employees (`GET /eligibility/report`, `/eligibility` page, nav link
    "Eligibility Report") showing Child, Age, Financial Year, Allotted,
    Utilized, In Progress, Balance, and Last Modified — computed live
    from claims the same way as the existing HR Eligibility Utilization
    report. See `DECISIONS_LOG.md` items 40-41.
  - Tests: 1 new claim test (view history + resubmit a SentBack claim)
    and a new `test_eligibility.py` (4 tests, including a route-ordering
    regression test for `/eligibility/report` vs `/eligibility/{child_id}`)
    — 109 backend tests total, all passing; `ruff`/`mypy` clean. Frontend
    `build`/`lint` clean.
  - Verified against the real database and the running dev servers
    (backend restarted; frontend hot-reloaded with no errors).

- Login-page employee autocomplete added on 2026-09-19, per direct user
  request. Flagged first: this required a genuine, accepted tradeoff
  against the existing no-enumeration login design (see
  `DECISIONS_LOG.md` item 42) — `GET /auth/active-employees` is
  deliberately public (no auth) since it feeds the login page before the
  user has a token, and returns every active employee's ID + name to
  anyone who can reach the API. The user chose to accept this tradeoff
  over a throttled/partial version or not building it. The login page's
  Employee ID field is now a combobox: it still accepts free typing, and
  filters the fetched active-employee list client-side as you type,
  matching against either ID or name — if the list fails to load, typing
  still works normally.
  - Tests: 2 new backend tests (public access confirmed; inactive/
    null-active employees correctly excluded) — 111 backend tests total,
    all passing; `ruff`/`mypy` clean. Frontend `build`/`lint` clean.
  - Verified against the real database: the endpoint returns exactly the
    two real active employees on file.

- Eligibility rollover logic added on 2026-09-20, per direct user
  request, resolving part of the gap `DECISIONS_LOG.md` item 13 had
  explicitly deferred. `add_child` now also creates a next-financial-year
  eligibility record by default (in addition to the current FY's), capped
  at the child's 72nd month/6th birthday — skipped when that cutoff
  already falls within the current FY. Two new pure functions in
  `eligibility_calculator.py` (`next_financial_year_window`,
  `next_financial_year_needed`), both unit-tested directly. This is
  scoped to exactly one year ahead at child-creation time, not an ongoing
  scheduled rollover for existing children in later years — see
  `DECISIONS_LOG.md` item 43 for the exact boundary and what's still not
  covered.
  - Existing endpoints (`GET /eligibility`, `GET /eligibility/{child_id}`,
    the employee eligibility report) already return every eligibility row
    for a child, so the new next-FY row shows up automatically — no
    frontend changes were needed.
  - Tests: 4 new pure unit tests plus 2 new integration tests (next-FY
    row created; skipped when the cutoff is this FY) — updated 3 existing
    tests that had assumed exactly one eligibility row per child. 118
    backend tests total, all passing; `ruff`/`mypy` clean.
  - Verified against the real database and the running backend (restarted
    to pick up the change).

- Payout calculation, first slice, added on 2026-09-20 per direct user
  request — see `DECISIONS_LOG.md` item 44 for the full rationale and
  scope boundary. `Childcare_EligibilityMaster`'s ApprovedAmount/
  UtilizedAmount/InProgressAmount/RemainingAmount are now real, maintained
  balances instead of frozen at their initial values:
  - New `app/services/eligibility_balance_service.sync_balance` recomputes
    a child+FY's Approved and In Progress totals from scratch from actual
    claims, called after every claim submit/approve/reject/send-back.
  - HR's approve action now rejects an amount exceeding the child's
    current remaining balance for that financial year, alongside the
    pre-existing invoice-amount cap — validated against a row-locked read
    to prevent a race between two concurrent approvals.
  - The My Children page's "Remaining" figure (and the Add Child flow)
    now shows real, non-zero values once claims are approved, with no
    frontend change needed — it already read this column, which had
    simply always been zero before. The HR approve form now caps/defaults
    to and displays the real remaining balance.
  - Tests: 5 new integration tests (`test_eligibility_balance.py`)
    covering submit → in-progress increases, approve → moves to approved,
    HR blocked from over-approving cumulative claims past the balance,
    reject/send-back → removed from in-progress, resubmit → restored. 123
    backend tests total, all passing; `ruff`/`mypy` clean. Frontend
    `build`/`lint` clean.
  - Verified against the real database: found (and, with the user's
    explicit go-ahead, backfilled) two real eligibility rows whose balance
    columns predated this feature and were stale relative to already-
    Approved/Submitted claims — see item 44 for the exact before/after
    figures.

- Payout Increment 1 — pure calculation engine, completed 2026-09-20, per
  `PAYOUT_REQUIREMENTS.md` (finalized the same day; see `DECISIONS_LOG.md`
  items 44-48). No database changes — `app/services/payout_calculator.py`
  is a dependency-free, side-effect-free module (same pattern as
  `eligibility_calculator.py`) that takes one child's one financial
  year's eligible-month window plus its approved claims (amount +
  approval timestamp) and returns the monthly ledger and per-claim
  allocation, entirely in memory.
  - Confirmed by hand-tracing against every number in
    `PAYOUT_REQUIREMENTS.md`'s worked examples before writing any test:
    a claim's "catch-up" (unconsumed entitlement up to and including its
    own approval month) is billed as one row dated at that approval
    month — not split back across the origin months it drew from — while
    genuinely future months each get their own row as the claim spills
    forward. A real bug was caught this way during implementation: the
    first draft attributed the monthly ledger's "allocated" figure to
    whichever month's raw capacity was physically drawn from, which
    silently disagreed with the spec's own September figure (₹9,000
    expected, ₹14,000 computed, because a later claim's catch-up had
    reached back into September's leftover) — fixed by aggregating the
    ledger from the allocation rows' attributed month instead.
  - 12 new unit tests (`test_payout_calculator.py`): the full three-claim
    worked example from `PAYOUT_REQUIREMENTS.md` §18 verified figure-for-
    figure (both allocations and the monthly ledger), chronological
    ordering by approval time regardless of input order, a claim exactly
    exhausting all remaining capacity, a claim exceeding total capacity
    raising `PayoutCapacityExceededError` (should be unreachable given
    the existing approval-time cap — asserted rather than silently
    handled), and eligibility-window boundary cases. 135 backend tests
    total, all passing; `ruff`/`mypy` clean.
  - Not yet built (future increments, each pending its own go-ahead):
    persisting to `Childcare_PayoutMonthlyLedger`/`Childcare_
    PayoutAllocation`, wiring the recompute into `hr_service.
    approve_claim`, `Childcare_PayoutAdjustment`, and the employee-facing
    payout schedule view.

- Payout Increment 2 — persistence, completed 2026-09-20. Migration
  `8361f7a48ffe` adds `Childcare_PayoutMonthlyLedger` and `Childcare_
  PayoutAllocation`; `app/services/payout_service.recalculate_payout`
  wires Increment 1's pure calculator to the database, called from
  `hr_service.approve_claim` after every approval (a full delete-and-
  regenerate for that EligibilityID, per `PAYOUT_REQUIREMENTS.md` §7).
  Still nothing user-facing — no API endpoint reads these tables yet.
  - A real bug was caught applying the migration: `EligibilityID` must be
    `BIGINT` to match `Childcare_EligibilityMaster`'s actual primary key
    type; SQL Server rejected the foreign key with `INT` (fixed before
    the table was ever successfully created — no data was affected).
  - Tests: 3 new integration tests (`test_payout_service.py`) reproduce
    `PAYOUT_REQUIREMENTS.md` §18's exact three-claim worked example
    end-to-end through the real API and real database — including
    deliberately backdating `Childcare_ClaimApprovalHistory.ActionDate`
    in the test (payout allocation is anchored to the real approval
    timestamp, so claims approved seconds apart in one test run would
    otherwise all land in the same real calendar month and never
    exercise cross-month spillover). 138 backend tests total, all
    passing; `ruff`/`mypy` clean.
  - With the user's go-ahead, backfilled Krishna's real payout ledger
    (EligibilityID 176) from her 3 already-approved claims' real,
    un-backdated approval timestamps — all landed in September 2026
    (when they were genuinely approved), totaling ₹41,140, matching her
    existing eligibility balance.
  - Not yet built: `Childcare_PayoutAdjustment`, the employee/HR-facing
    payout schedule view, `Childcare_PayoutSummary`.

- Payout Increment 3 — schedule visibility, completed 2026-09-20, per
  `PAYOUT_REQUIREMENTS.md` §16 ("a clear employee view showing when an
  approved claim will actually be paid"). Both `GET /claims/{id}` and
  `GET /hr/claims/{id}` now include `payout_schedule` (one entry per
  month the claim pays out in, sourced from `Childcare_PayoutAllocation`
  via a new `payout_repository.get_allocations_for_claim`) — empty until
  the claim is Approved. Reused the existing `ClaimDetailPage.tsx`/
  `HRClaimDetailPage.tsx` pages (built in an earlier increment) rather
  than a new page, adding a "Payout Schedule" section that only renders
  once populated.
  - Tests: 1 new integration test verifying the schedule is empty before
    approval and matches exactly (both on the HR approve response and on
    both parties' subsequent GETs) after approval. 139 backend tests
    total, all passing; `ruff`/`mypy` clean. Frontend `build`/`lint`
    clean.
  - Still not built: `Childcare_PayoutAdjustment`, `Childcare_
    PayoutSummary`, the aggregate monthly-ledger view (this increment
    only exposes a single claim's own schedule, not the full child+FY
    ledger with entitlement/carry-forward detail).

- Payout Increment 4 — aggregate monthly ledger view, completed
  2026-09-20. `GET /eligibility/{child_id}/payout-schedule?financialYear=`
  returns the full month-by-month ledger (entitlement, opening balance,
  available, allocated, adjustment, closing balance, calculated payout)
  for one of the employee's own children in one financial year — the
  child+FY-level complement to Increment 3's per-claim schedule. Surfaced
  via a new "Monthly Schedule" link on each Eligibility Report row,
  opening a new `PayoutScheduleDetailPage.tsx` at
  `/eligibility/:childId/schedule?fy=`.
  - Tests: 4 new integration tests (`test_payout_schedule_endpoint.py`) —
    auth required, 404 for an unknown financial year, ownership scoping
    (can't see another employee's child), and the full ledger including
    zero-allocation months, verified against a real approval. 143 backend
    tests total, all passing; `ruff`/`mypy` clean. Frontend `build`/`lint`
    clean.
  - Verified against real data: Krishna's real ledger (backfilled in
    Increment 2) reads correctly through this endpoint's underlying query.
  - Still not built: `Childcare_PayoutAdjustment`, `Childcare_
    PayoutSummary`.

- Payout Increment 5 — HR payout report + employee-view discoverability,
  completed 2026-09-20, per direct user request. New `GET
  /hr/reports/payout` (HR-only), filterable by financial year, employee
  ID, and child ID — the Employee + Child + FY, April-through-March
  pivoted report `PAYOUT_REQUIREMENTS.md` §9 originally proposed as a
  stored `Childcare_PayoutSummary` table, built instead as a live query
  over `Childcare_PayoutMonthlyLedger` (same pattern as every other HR
  report). On-screen table plus CSV export. Added as a new "Payout" tab
  on the existing HR Reports page.
  - The user also asked that "employee should have a view to their child
    payout" — judged already satisfied by Increments 3-4 (a claim's own
    payout schedule on its detail page; the child+FY monthly ledger
    reachable from the Eligibility Report). Rather than build a
    duplicate page, improved discoverability instead: renamed the nav
    link and page heading from "Eligibility Report" to "Eligibility &
    Payout", with the monthly-schedule drill-down called out explicitly
    in the page description.
  - Recorded, but not yet implemented: the user's answer to the
    adjustment-validation question raised at the end of Increment 4 —
    "for now trust the HR" — no bounds/validation when `Childcare_
    PayoutAdjustment` is eventually built.
  - Tests: 4 new integration tests (`test_payout_report.py`) — HR-only
    auth, empty-when-nothing-approved, the Apr-Mar breakdown and all
    three filters against a real approval, and CSV format. 147 backend
    tests total, all passing; `ruff`/`mypy` clean. Frontend `build`/
    `lint` clean.
  - Verified against real data: the report correctly shows Krishna's real
    ₹41,140 (backfilled in Increment 2) attributed to September 2026.
  - Still not built: `Childcare_PayoutAdjustment` itself.

- Payout report/layout follow-ups, completed 2026-09-20, per direct user
  request:
  - Added `child_dob` and an explicit Employee ID column to the payout
    report shape (`PayoutReportRow`) — shown on both HR's and the
    employee's payout report tables. Sourced from `ChildMaster` via the
    same batch child lookup already used for `child_name` (asserted
    non-null: `ChildID` is a foreign key on `Childcare_
    PayoutMonthlyLedger`, so the row is guaranteed to exist).
  - Added `GET /eligibility/payout-report` (employee-auth) — reuses
    `report_service.build_payout_report` exactly as HR's endpoint does,
    just always scoped to the caller's own `EmployeeID` rather than
    exposing an employee filter. New "My Payout" page/nav link shows the
    same Apr-Mar table HR sees, scoped to the employee's own children.
    Factored the table markup into a shared `components/
    PayoutReportTable.tsx` used by both HR's and the employee's page,
    rather than duplicating it.
  - Widened the overall application shell: `AppLayout.tsx`'s header and
    main content container went from `max-w-5xl` (1024px) to `max-w-7xl`
    (1280px). This directly widens every page that has no narrower
    wrapper of its own (My Claims, HR Queue, Reports, Eligibility &
    Payout, My Payout) — exactly the table-heavy pages that needed it,
    including the 18-column payout tables. Detail/form pages that
    already had their own inner `max-w-*` (Claim Detail, HR Claim Detail,
    Add Child, the Raise Claim wizard) are unaffected and keep their
    existing, more readable widths.
  - Tests: 1 new integration test (employee payout report is correctly
    scoped to the caller's own children) plus `child_dob` assertions
    added to the existing payout report tests. 148 backend tests total,
    all passing; `ruff`/`mypy` clean. Frontend `build`/`lint` clean.
  - Verified against real data: the report now shows real children's DOB
    and Employee ID correctly.

- HR Claim Detail page UX improvements, completed 2026-09-20, per direct
  user request:
  - **Claim history popup**: a "View claim history" link opens a modal
    listing every other claim for the same employee+child (linking to
    each one's own detail page). Backend: `GET /hr/claims` gained
    optional `employee_id`/`child_id` filters (`claim_repository.
    get_claims_for_hr`, `hr_service.list_claims`), reusing the existing
    endpoint rather than adding a new one.
  - **Visual hierarchy**: the Invoice section now has a colored left
    accent border and a subtly tinted background to draw the eye first.
  - **Reordered sections**: Documents now comes before Eligibility
    (previously Eligibility was second, before Documents).
  - **Collapsible sections**: Eligibility and Payout Schedule are now
    collapsible (new `components/CollapsibleSection.tsx`, built on native
    `<details>/<summary>`, no extra JS state), open by default.
  - New reusable `components/Modal.tsx` (dependency-free, closes on
    backdrop click, X, or Escape) backs the claim history popup and can
    be reused for future popups.
  - Tests: 1 new integration test (`GET /hr/claims` employee+child
    filtering, confirming a different child's claims aren't mixed in).
    149 backend tests total, all passing; `ruff`/`mypy` clean. Frontend
    `build`/`lint` clean.

- Reports/CSV follow-ups, completed 2026-09-20, per direct user request:
  - **Claims Summary report**: added `approved_date` (the claim's
    `Approved` `ClaimApprovalHistory` entry's timestamp, `None` if never
    approved — `report_repository.get_approved_dates_by_claim`) and
    surfaced both it and the already-existing-but-unused `submitted_date`
    as new "Submitted"/"Approved" columns on the on-screen table.
  - **HR Claim Detail page**: added a "Submitted date" line to the
    Invoice section — deliberately *not* an approved date there too,
    since the History section already shows exactly when/by whom it was
    approved.
  - **My Payout page**: added an "Export CSV" button, matching every
    other report in the app. Backend: `GET /eligibility/payout-report`
    gained `format=csv` support, reusing the exact same CSV-writing logic
    as HR's reports — extracted the shared `_csv_response` helper (previously
    private to `reports.py`) into `app/api/v1/csv_response.py` so both
    endpoints use one implementation.
  - Tests: 1 new assertion pair on the existing Claims Summary test
    (submitted/approved dates present/absent correctly) plus 1 new CSV
    test for the employee payout report. 150 backend tests total, all
    passing; `ruff`/`mypy` clean. Frontend `build`/`lint` clean.

- Home page dashboard, completed 2026-09-20, per direct user request —
  replaced the Increment 1 placeholder (a bare backend-connectivity check)
  with a real dashboard. Frontend-only; no backend changes, since every
  data point was already available from existing endpoints.
  - Every employee sees: shortcut buttons (Raise Claim, My Claims, My
    Payout, Eligibility & Payout), stat cards (children, active claims,
    total payout, remaining balance), a recent-claims list, and a
    monthly-payout bar chart summed across all their children/financial
    years (via the existing `GET /eligibility/payout-report`).
  - HR approvers additionally see an "HR Overview" section: shortcuts
    (HR Queue, Reports), stat cards (pending review, employees with
    children, total approved payout), and a claims-by-status bar chart.
  - The chart is a new, dependency-free `components/BarChart.tsx` (plain
    proportionally-scaled divs) rather than adding a charting library —
    flagged to the user beforehand as the one real tradeoff (less
    polished than a real charting library, but keeps the app
    dependency-free; revisit if richer/interactive charts are wanted
    later). Also added a reusable `components/StatCard.tsx`.
  - The old connectivity check was kept (still useful for diagnosing a
    misconfigured `VITE_API_BASE_URL`) but demoted to a small, quiet strip
    at the very bottom of the page instead of the page's main content.
  - Verified: frontend `build`/`lint` clean; no backend changes, so the
    existing 150 backend tests are unaffected.

## Next
Exact payout calculation and carry-forward rules remain unresolved (see
`CODEX_MASTER_INSTRUCTIONS.md` §12) — that resolution is needed before
"Finalize and implement payout" (roadmap item 10) can be built without
guessing. Docker/deployment hardening (roadmap item 13) — e.g. a
DB/MinIO-connectivity readiness probe alongside the existing
dependency-free liveness check, and the reverse-proxy/TLS setup
`DEPLOYMENT.md` describes — is the remaining vertical slice that doesn't
depend on it, when explicitly requested.
