import pytest

from app.core.config import Settings
from app.core.security import TokenError, create_access_token, decode_access_token


def _settings_with(**overrides: object) -> Settings:
    """Build a Settings instance isolated from any local .env file.

    Deleting JWT_SECRET_KEY from os.environ would not be enough on its own:
    a developer's real backend/.env (which legitimately holds a working
    local secret) would still supply it as a fallback. These tests must be
    able to exercise "no secret configured" regardless of what's in that
    file.
    """
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


@pytest.fixture()
def configured_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = _settings_with(jwt_secret_key="test-secret-do-not-use-in-production")
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings)
    return settings


@pytest.fixture()
def unconfigured_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = _settings_with(jwt_secret_key="")
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings)
    return settings


def test_create_and_decode_access_token_roundtrip(configured_settings: Settings) -> None:
    token = create_access_token(employee_id="12345678", memp_id=42)

    payload = decode_access_token(token)

    assert payload["sub"] == "12345678"
    assert payload["memp_id"] == 42


def test_decode_rejects_tampered_token(configured_settings: Settings) -> None:
    token = create_access_token(employee_id="12345678", memp_id=42)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_decode_rejects_garbage_token(configured_settings: Settings) -> None:
    with pytest.raises(TokenError):
        decode_access_token("not-a-jwt")


def test_create_access_token_requires_secret(unconfigured_settings: Settings) -> None:
    with pytest.raises(RuntimeError):
        create_access_token(employee_id="12345678", memp_id=42)


def test_decode_access_token_requires_secret(
    configured_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = create_access_token(employee_id="12345678", memp_id=42)

    unconfigured = _settings_with(jwt_secret_key="")
    monkeypatch.setattr("app.core.security.get_settings", lambda: unconfigured)

    with pytest.raises(RuntimeError):
        decode_access_token(token)
