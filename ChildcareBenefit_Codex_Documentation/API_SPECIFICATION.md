# API Specification

Base: `/api/v1`

## Auth
`POST /auth/login`
Input: employeeId.
Lookup `Master_Emp_BasicInfo`; require active employee.

`GET /me`

## Children
`GET /children`
`POST /children`
`GET /children/{childId}`
`PUT /children/{childId}`

POST must atomically create child and eligibility.

## Eligibility
`GET /eligibility?financialYear=2026-27`
`GET /eligibility/{childId}?financialYear=2026-27`

## Claims
`GET /claims`
`POST /claims`
`PUT /claims/{claimId}`
`POST /claims/{claimId}/submit`
`GET /claims/{claimId}`

## Attachments
`POST /claims/{claimId}/attachments`
`GET /claims/{claimId}/attachments`

## HR
`GET /hr/claims`
`GET /hr/claims/{claimId}`
`POST /hr/claims/{claimId}/approve`
`POST /hr/claims/{claimId}/reject`
`POST /hr/claims/{claimId}/send-back`

All endpoints require server-side validation and authorization.
