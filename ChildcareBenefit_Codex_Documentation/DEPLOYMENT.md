# Deployment

Separate Development, UAT and Production configuration.

Docker-ready:
- React frontend
- FastAPI backend
- MinIO
- SQL Server may remain organization-managed.

Use environment variables/secrets for DB, MinIO, auth, CORS and limits.

Production:
- HTTPS
- Reverse proxy/load balancer as appropriate
- Private MinIO
- Restricted DB access
- Backups
- Monitoring
- Centralized logs
- Health/readiness checks

Define SQL Server and MinIO backup/recovery and document retention according to organizational policy.
