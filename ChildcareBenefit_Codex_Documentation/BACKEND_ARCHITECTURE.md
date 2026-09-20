# Backend Architecture

FastAPI + SQL Server + MinIO.

## Layers
- API routes
- Schemas
- Services/business logic
- Repositories/data access
- Models
- Dependencies
- Core configuration/security/logging

## Rules
- Use `/api/v1`.
- Use parameterized database operations.
- Use connection pooling.
- No hardcoded secrets.
- Centralized exception handling.
- Safe error responses.
- Structured logging.
- Correlation IDs.
- Explicit transaction boundaries.
- Eligibility logic belongs in one dedicated service.
- Approval and balance updates must be concurrency-safe.
