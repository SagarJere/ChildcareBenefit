from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "environment" in body


def test_health_response_has_correlation_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert "X-Correlation-ID" in response.headers


def test_health_does_not_require_database() -> None:
    """The health endpoint must respond even when SQL Server is unreachable
    or unconfigured, so it can be used for early liveness checks."""
    import os

    for key in ("MSSQL_SERVER", "MSSQL_DATABASE", "MSSQL_USERNAME", "MSSQL_PASSWORD"):
        os.environ.pop(key, None)

    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/health")

    assert response.status_code == 200
