# Database Scripts

This folder holds one-off SQL Server scripts that fall outside the Alembic
migration chain in `database/migrations/` — for example, DBA-run scripts to
provision a least-privilege application login, or organization-specific
setup that cannot be expressed as a portable migration.

No scripts are required for Increment 1 (project foundation). Add scripts
here as they become necessary, with a comment at the top of each script
explaining its purpose and when it should be run.
