# Childcare Benefit

Production-ready enterprise application for managing employee childcare
benefit eligibility and claims. See
`ChildcareBenefit_Codex_Documentation/` for the full requirements, business
rules, and architecture that govern this project.

**Current status:** Increment 1 (Project Foundation), Increment 2
(Employee Login), Increment 3 (Child Management + Eligibility),
Increment 4 (Claims + Document Upload), Increment 5 (HR Approval
Workflow), Increment 6 (Reports), and Increment 7 (Security & Performance
Testing) are complete. Payout is not implemented yet (its rules are not
finalized — see
`ChildcareBenefit_Codex_Documentation/CODEX_MASTER_INSTRUCTIONS.md` §12).

No one has HR access by default — grant it by inserting a row into
`Childcare_HRApprovers` (`EmployeeID`, `IsActive`); there is no
management UI for this table.

## Stack

- **Frontend:** React + Vite + TypeScript, Tailwind CSS, React Router,
  Axios, TanStack Query, React Hook Form, Zod, Lucide React, Sonner
- **Backend:** FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database:** Microsoft SQL Server
- **Object storage:** MinIO (used for claim document upload/download)

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- A reachable SQL Server instance — required for login, child
  management, and claims (the health endpoint still works without one).
- A reachable MinIO (or S3-compatible) instance — required only for
  uploading/downloading claim documents.

## Backend — setup and run

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env    # Windows; use `cp` on macOS/Linux
# edit .env with real values as needed

uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Interactive docs:
`http://localhost:8000/api/docs`. Health check:
`http://localhost:8000/api/v1/health`.

Employee Login (`POST /api/v1/auth/login`, `GET /api/v1/me`) additionally
requires `JWT_SECRET_KEY` to be set in `backend/.env` — generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Login also requires SQL Server to be configured (`MSSQL_*` in
`backend/.env`), since it queries the real `Master_Emp_BasicInfo` table.

Claim document upload/download (`POST`/`GET .../attachments...`)
additionally requires `MINIO_*` to be set in `backend/.env`; every other
claim endpoint works without it.

### Local MinIO (development only)

MinIO's official binary distribution was discontinued after this project
started (see `DECISIONS_LOG.md` item 24); for local development a copy of
the last available Windows release lives at `.minio/bin/minio.exe`
(gitignored), with its data at `.minio/data/`. To start it:

```powershell
$env:MINIO_ROOT_USER = "admin"
$env:MINIO_ROOT_PASSWORD = "<the password in backend/.env's MINIO_SECRET_KEY>"
& ".minio\bin\minio.exe" server ".minio\data" --address ":9000" --console-address ":9001"
```

API: `http://localhost:9000`. Web console: `http://localhost:9001` (sign
in with the credentials above). `backend/.env`'s `MINIO_ENDPOINT`,
`MINIO_ACCESS_KEY`, and `MINIO_SECRET_KEY` must match whatever you start
it with. In production, point `MINIO_*` at a real MinIO or S3-compatible
deployment instead — the application code doesn't care which.

### Backend tests / lint / type-check

```bash
cd backend
pytest
ruff check .
mypy app
```

`test_auth.py`, `test_children.py`, `test_claims.py`, `test_hr.py`,
`test_reports.py`, and `test_security_hardening.py`'s integration tests
run against a real SQL Server database (inside a transaction that's
always rolled back, so nothing is left behind) and are skipped — not
faked — when `MSSQL_*` isn't configured. Tests that upload a real file to
MinIO clean it up themselves in a `finally` block, since the upload isn't
part of the rolled-back DB transaction; they're skipped until `MINIO_*`
is set.

### Database migrations (Alembic)

Migration scripts live in `database/migrations/`; the Alembic config
(`backend/alembic.ini`) reads the SQL Server connection string from the same
environment variables as the running app. Requires `MSSQL_*` variables to be
set in `backend/.env`.

```bash
cd backend
alembic upgrade head
```

Increment 3 adds `Childcare_FinancialYearMaster`, `Childcare_ChildMaster`,
and `Childcare_EligibilityMaster`; Increment 4 adds `Childcare_
ClaimMaster` and `Childcare_ClaimAttachments`; Increment 5 adds
`Childcare_HRApprovers` and `Childcare_ClaimApprovalHistory`; a later
migration adds an optional `Comments` column to `Childcare_ClaimMaster`.
`Master_Emp_BasicInfo` is untouched — run `alembic upgrade head` before
using Child Management, Claims, or HR.

## Frontend — setup and run

```bash
cd frontend
npm install
copy .env.example .env.local    # Windows; use `cp` on macOS/Linux
npm run dev
```

The app is served at `http://localhost:5173` and expects the backend to be
reachable at the URL configured in `VITE_API_BASE_URL`.

### Frontend build / lint

```bash
cd frontend
npm run build
npm run lint
```

## Docker

A `docker-compose.yml` at the repository root runs the backend, frontend,
a local SQL Server container, and a local MinIO container for development.
Copy `.env.example` to `.env` at the repository root first.

```bash
docker compose up --build
```

In UAT/Production, SQL Server is typically an organization-managed
instance rather than the containerized one (see
`ChildcareBenefit_Codex_Documentation/DEPLOYMENT.md`).

## Project structure

```text
ChildcareBenefit/
├── frontend/            React + Vite + TypeScript app
├── backend/              FastAPI app
├── database/
│   ├── migrations/       Alembic migration scripts
│   └── scripts/          Ad-hoc DBA scripts outside the migration chain
├── docs/                 Reserved for project docs beyond the source-of-truth
│                         Markdown in ChildcareBenefit_Codex_Documentation/
├── docker-compose.yml
└── .env.example
```

## Development process

This project is built in small, fully-tested increments — see
`ChildcareBenefit_Codex_Documentation/DEVELOPMENT_ROADMAP.md` and
`DEVELOPMENT_PROGRESS.md` for what has been completed and what is next.
