# Code Quality Standard

No:
- TODO production placeholders
- mock APIs in production paths
- fake repositories
- hardcoded employee/business data
- silent exception swallowing
- hardcoded secrets
- unvalidated uploads
- commented-out incomplete production logic
- "implement later" executable paths

Every feature must include:
1. Database implementation
2. Backend API
3. Business logic
4. Validation
5. Authorization
6. Frontend integration
7. Loading/error/empty states
8. Automated tests
9. Documentation

If a business rule is ambiguous, do not guess. Request clarification.
