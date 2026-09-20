# Roles and Authorization

## Employee
Can view own data, manage own children, view own eligibility, create/update/submit own claims and documents.

Cannot view other employees or approve claims.

## HR
Can review authorized claims, documents, eligibility, enter approved amount and Approve/Reject/Send Back.

## Backend
Authorization must be enforced by FastAPI, not merely by hiding React controls.
