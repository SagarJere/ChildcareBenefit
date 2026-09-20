# Codex Master Instructions - Childcare Benefit

You are implementing the **Childcare Benefit** application as a production-ready enterprise application.

## 1. Absolute Development Standard

This is NOT a demo, prototype, tutorial, sample project, or proof of concept.

Do not produce:
- Half-baked code
- Mock production implementations
- Fake APIs
- Fake repositories
- Hardcoded employee/business data
- TODO implementation placeholders
- `pass` used as a substitute for implementation
- "Implement later" executable code
- Silent exception swallowing
- Unvalidated file uploads
- Incomplete screens
- Commented-out unfinished production logic

Every completed development increment must be fully implemented, integrated, validated, authorized, tested, and documented.

---

# 2. CRITICAL: BUILD IN SMALL INCREMENTS

## Do NOT build the entire application at once.

Do not generate the complete application in one response or one development operation.

Do not build an entire large module in one go unless the user explicitly asks for it.

The application must be developed **increment by increment**.

### Development Rule

> **Implement ONLY the current requested increment. Complete it fully. Test it. Verify it. Then wait for the user to request the next increment.**

Do not proactively implement future increments.

Do not create unrelated future modules just because their requirements are already documented.

### Example

If the current request is:

`Implement Employee Login UI`

Implement only the login UI and everything strictly required to make that increment complete.

Do NOT simultaneously build:
- Child Management
- Eligibility
- Claims
- HR Approval
- Payout
- Reports

### Another Example

If the current request is:

`Implement ChildID generation`

Implement the complete ChildID generation functionality and its required validation/tests.

Do NOT build the entire Child Management module unless explicitly requested.

---

# 3. Increment Completion Standard

Every increment must be considered a small production feature.

For the current increment:

1. Understand the requirement.
2. Inspect the existing repository/code before modifying it.
3. Identify dependencies.
4. Make only the necessary database changes.
5. Implement backend logic.
6. Implement API endpoints if required.
7. Implement frontend changes if required.
8. Implement validation.
9. Implement authorization where applicable.
10. Implement error handling.
11. Add automated tests.
12. Run tests/lint/type checks where applicable.
13. Fix failures.
14. Verify integration.
15. Update relevant documentation/progress.
16. Clearly report what was changed.
17. Stop.

Do not continue into the next increment automatically.

---

# 4. Technology Stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: Microsoft SQL Server
- Object Storage: MinIO
- API: REST/JSON
- UI: Modern responsive enterprise design
- Deployment: Docker-ready

Use maintained current stable package versions available at implementation time.

---

# 5. Existing Employee Master

Use the existing:

`Master_Emp_BasicInfo`

Fields (verified against the actual `ChildcareBenefit` database on
2026-09-19; there is no `Gender` column and the active flag is `IsActive`,
not `Inactive` — see `DATABASE_DESIGN.md`):
- MEmpID
- EmployeeID
- FullName
- MySingleID
- Joindate
- IsActive

Do NOT create a duplicate employee master.

Use `MEmpID` as the internal relationship key where the actual SQL data type supports it.

Use `EmployeeID` as the business/display identifier.

---

# 6. Version 1 Login

Version 1 login accepts Employee ID.

The backend must:
1. Receive Employee ID.
2. Query `Master_Emp_BasicInfo`.
3. Verify employee exists.
4. Verify employee is active (`IsActive = 1`; treat NULL as not active).
5. Return employee details through the defined authentication/session boundary.

Employee-ID-only login is an initial/internal authentication mode and is not considered sufficient production authentication.

The architecture must keep authentication isolated so an approved organization SSO / Microsoft Entra ID mechanism can replace it later.

---

# 7. Childcare Business Rules

- Benefit: ₹14,000 per month per eligible child.
- Maximum 2 children per employee.
- Financial year: April through March.
- ChildID format: `EmployeeId_ChildSequenceNo`.
- Examples: `12345678_1`, `12345678_2`.
- Child sequence is 1 or 2.
- Eligibility is automatically calculated whenever a new child is added.
- Eligibility starts from the latest applicable month among:
  - Financial year start month
  - Employee joining month
  - Child birth month
- Benefit ends at the child's six-year eligibility limit.
- First 12 child months require no bills.
- From child month 13 onward, invoice/receipt and payment proof are required.

---

# 8. Eligibility Creation

Adding a child must be implemented as a complete transactional operation:

1. Validate authenticated employee.
2. Verify employee is active.
3. Verify employee has fewer than two children.
4. Generate ChildID server-side.
5. Create Child Master record.
6. Calculate applicable eligibility.
7. Create/update the eligibility record.
8. Commit only when the complete operation succeeds.

If a required step fails, use an appropriate rollback/recovery strategy.

Do not leave orphan child or eligibility records.

Eligibility calculation must live in a dedicated service/domain component and must not be duplicated across multiple endpoints.

---

# 9. Claims

Employees can raise claims for a specific child.

Claim data includes:
- Invoice date
- Invoice number
- Invoice amount
- Receipt/invoice
- Payment proof

Claim workflow:

`Draft → Submitted → HR Review → Approved / Rejected / Sent Back`

A Sent Back claim can be corrected and resubmitted.

---

# 10. Claim Documents

Use MinIO for actual document storage.

SQL Server stores document metadata and MinIO object references.

Use a private bucket.

Recommended object key:

`claims/{EmployeeId}/{ChildID}/{ClaimID}/{UUID}-{safe-name}`

Documents must be:
- Validated
- Size-limited
- Type/extension validated
- Assigned server-generated object names
- Protected by authorization

Employees may access only their own documents.

HR may access documents only when authorized for the claim.

Do not expose MinIO credentials to the frontend.

---

# 11. HR Workflow

HR can:
- Review claims
- View supporting documents
- Enter approved amount
- Approve
- Reject
- Send Back
- Add remarks

Every HR action must be recorded in an audit/history table.

Backend authorization is mandatory. Hiding buttons in React is not authorization.

---

# 12. Payout

Updated 2026-09-20: the user has now finalized carry-forward behavior,
monthly payout semantics, and multiple-claim handling — see
`PAYOUT_REQUIREMENTS.md` for the complete, confirmed rules, and
`DECISIONS_LOG.md` items 44-48 for the reasoning behind each one. That
document supersedes this section for everything it covers.

What is still NOT finalized, and must still not be guessed:
- Excess invoice handling beyond what `PAYOUT_REQUIREMENTS.md` §6
  already covers (it can't happen in practice — see the mathematical
  argument there — but if that assumption is ever found to not hold,
  stop and ask rather than inventing a fallback)
- Actual money disbursement / payroll integration ("Actual Payment")
- The "Admin" role mentioned in `PAYOUT_REQUIREMENTS.md` §8 (deferred,
  undefined)
- Anything involving cancelling or reversing an already-Approved claim
  (explicitly out of scope — Approved is terminal, per item 46)

When implementation reaches a point that depends on a rule not covered by
`PAYOUT_REQUIREMENTS.md`, stop and ask the user for the business
decision.

---

# 13. Security

- No secrets in source code.
- Use environment variables/secret management.
- HTTPS in production.
- Restrict CORS.
- Validate all server inputs.
- Enforce backend authorization.
- Do not trust EmployeeId supplied by the browser for ownership checks.
- Use parameterized SQL/ORM mechanisms.
- Use least-privilege database access.
- Keep MinIO private.
- Use secure document access.
- Do not log passwords, tokens, secrets or document contents.
- Audit sensitive business actions.

---

# 14. Frontend Standards

Use:
- React + Vite
- React Router
- Tailwind CSS
- shadcn/ui
- React Hook Form
- Zod
- Axios
- TanStack Query
- Lucide React
- Sonner

The UI must be:
- Modern
- Responsive
- Accessible
- Visually intuitive
- Consistent
- Usable on desktop, tablet and mobile

Every relevant screen must include proper:
- Loading state
- Empty state
- Error state
- Success feedback
- Validation messages

Do not use fake data in production paths.

---

# 15. Backend Standards

Use clear separation between:
- API routes
- Schemas
- Services/business logic
- Repositories/data access
- Models
- Dependencies
- Core configuration/security/logging

Use `/api/v1`.

Use explicit transaction boundaries.

Implement centralized exception handling.

Never expose stack traces or internal database errors to users.

---

# 16. Database Standards

Use:
- Primary keys
- Foreign keys where appropriate
- Unique constraints
- Check constraints where appropriate
- Appropriate indexes
- Audit fields
- Proper decimal precision for money
- Transaction-safe operations

Verify actual existing table data types before creating relationships to `Master_Emp_BasicInfo`.

Do not add redundant calculated fields unless their consistency/update strategy is clearly defined.

---

# 17. Testing Is Mandatory

Every increment must include appropriate tests.

Test business rules such as:
- Financial year calculation
- Joining date scenarios
- Child DOB scenarios
- Six-year limit
- Eligible month calculation
- ₹14,000 calculation
- Two-child limit
- ChildID generation
- Claim document requirements
- Claim status transitions
- HR actions

Also test negative and unauthorized scenarios.

Do not declare an increment complete while relevant automated tests are failing.

---

# 18. Code Quality Gate

Before declaring the current increment complete, verify:

- No TODO implementation remains.
- No placeholder implementation remains.
- No fake production API remains.
- No hardcoded production data remains.
- No secrets are hardcoded.
- Validation is implemented.
- Authorization is implemented where required.
- Error handling exists.
- Tests exist and pass.
- Frontend is integrated where required.
- Database scripts/migrations are complete.
- Responsive UI states are complete where applicable.
- Documentation is updated.

---

# 19. Handling Ambiguity

If a requirement is ambiguous but materially affects business behavior:

> **Do not guess. Ask for clarification.**

If the ambiguity does not materially affect the current increment, choose a standard maintainable implementation and document the decision.

Do not silently invent business rules.

---

# 20. Repository Discipline

Before changing code:
- Inspect the existing repository.
- Preserve working functionality.
- Avoid unnecessary rewrites.
- Do not overwrite unrelated work.
- Follow existing conventions when they are sound.
- Keep changes focused on the current increment.

After changes:
- Run relevant tests.
- Run lint/type checks.
- Verify the application starts.
- Verify the current increment end-to-end where possible.

---

# 21. Communication With the User

When finishing an increment, report:

### Completed
Exactly what was implemented.

### Files Changed
List important files.

### Database Changes
List migrations/scripts.

### Tests
List tests executed and their result.

### Verification
Explain how the increment was verified.

### Next Increment
Do not implement it. Only mention what could logically come next if useful.

Do not claim something is production-ready if it has not actually been implemented and verified.

---

# 22. Source of Truth

Use the Markdown documentation in this project as the requirements source.

Important documents include:
- PROJECT_REQUIREMENTS.md
- BUSINESS_RULES.md
- DATABASE_DESIGN.md
- API_SPECIFICATION.md
- FRONTEND_ARCHITECTURE.md
- UI_UX_REQUIREMENTS.md
- MINIO_DOCUMENT_STORAGE.md
- SECURITY.md
- TESTING_STRATEGY.md
- CODE_QUALITY_STANDARD.md
- DEVELOPMENT_ROADMAP.md
- DEVELOPMENT_PROGRESS.md

If the user's latest explicit instruction conflicts with an older document, treat the latest confirmed user requirement as authoritative and update the documentation.

---

# 23. Final Rule

## Build small. Build completely. Test completely. Stop.

Never build the entire application at once.

Never build a large module in one uncontrolled operation.

Implement the **smallest meaningful complete increment**, verify it, and wait for the next instruction.

The goal is a real production-quality Childcare Benefit application built carefully one increment at a time.
