# Login Requirements

Version 1 accepts Employee ID.

Lookup:
`Master_Emp_BasicInfo.EmployeeID`

Return:
- MEmpID
- EmployeeID
- FullName
- MySingleID
- Joindate

There is no `Gender` column on the actual table, so it is not returned
(see `DATABASE_DESIGN.md`).

Require active employee (`IsActive = 1`). `IsActive` is nullable on the
existing table; treat NULL as not active.

Employee-ID-only login is an initial/internal mode, not adequate production authentication. Keep authentication isolated so approved organization SSO/Entra ID can replace it later.

Backend authorization must not trust EmployeeId sent by the browser for ownership.
