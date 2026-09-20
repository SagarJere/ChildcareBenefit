# Combined single-service image for the free-tier deployment (Render): the
# FastAPI backend serves the built React frontend as static files from the
# same origin, so no separate frontend host or CORS setup is needed. Local
# development still uses backend/Dockerfile + frontend/Dockerfile separately
# via docker-compose.yml — this file is only for that combined deployment.

FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# Same-origin deployment: the frontend calls the API via a relative path,
# not an absolute URL.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# Pinned to bookworm (Debian 12) explicitly: the ODBC driver install below
# targets Microsoft's debian/12 package repo, and the floating
# "python:3.12-slim" tag has since moved to a newer Debian release.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ODBC Driver 18 for SQL Server + build tools needed by pyodbc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg unixodbc-dev gcc g++ \
    && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /app/dist ./static

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
