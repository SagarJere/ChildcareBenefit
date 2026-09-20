# Error Handling and Logging

Use consistent API errors:
- code
- message
- safe details
- correlationId

Suggested HTTP statuses:
400 validation/business error
401 unauthenticated
403 unauthorized
404 not found
409 conflict
413 file too large
422 validation
500 unexpected server error

Never return stack traces to clients.

Use structured server logs with timestamp, level, correlation ID, endpoint, operation and safe user context.

Frontend must show user-friendly actionable messages.
