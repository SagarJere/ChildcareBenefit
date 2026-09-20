import pytest

from app.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    """Build a Settings instance isolated from any local .env file.

    Without this, these tests would be at the mercy of whatever a developer
    happens to have in backend/.env (e.g. real local SQL Server settings),
    which is exactly the kind of ambient, hard-to-reproduce failure that
    should never affect a unit test.
    """
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_cors_origins_splits_and_trims_comma_separated_values() -> None:
    settings = make_settings(cors_allowed_origins="http://a.test, http://b.test ,http://c.test")

    assert settings.cors_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_sqlalchemy_uri_is_empty_when_database_not_configured() -> None:
    settings = make_settings(mssql_server="", mssql_database="", mssql_username="")

    assert settings.sqlalchemy_database_uri == ""


def test_sqlalchemy_uri_is_built_from_mssql_settings() -> None:
    settings = make_settings(
        mssql_server="db.internal",
        mssql_port=1433,
        mssql_database="ChildcareBenefit",
        mssql_username="svc_childcare",
        mssql_password="a-secret-value",
        mssql_driver="ODBC Driver 18 for SQL Server",
        mssql_encrypt=True,
        mssql_trust_server_certificate=False,
    )

    uri = settings.sqlalchemy_database_uri

    assert uri.startswith("mssql+pyodbc://svc_childcare:a-secret-value@db.internal:1433/ChildcareBenefit")
    assert "driver=ODBC+Driver+18+for+SQL+Server" in uri
    assert "Encrypt=yes" in uri
    assert "TrustServerCertificate=no" in uri


def test_sqlalchemy_uri_omits_port_when_not_set() -> None:
    settings = make_settings(
        mssql_server="localhost",
        mssql_port=None,
        mssql_database="ChildcareBenefit",
        mssql_username="svc_childcare",
        mssql_password="a-secret-value",
    )

    uri = settings.sqlalchemy_database_uri

    assert uri.startswith("mssql+pyodbc://svc_childcare:a-secret-value@localhost/ChildcareBenefit")


def test_blank_port_env_value_is_treated_as_unset() -> None:
    settings = make_settings(mssql_port="")

    assert settings.mssql_port is None


def test_windows_auth_mode_omits_credentials_and_adds_trusted_connection() -> None:
    settings = make_settings(
        mssql_auth_mode="windows",
        mssql_server="localhost",
        mssql_database="ChildcareBenefit",
    )

    uri = settings.sqlalchemy_database_uri

    assert uri.startswith("mssql+pyodbc://@localhost/ChildcareBenefit")
    assert "trusted_connection=yes" in uri


def test_windows_auth_mode_is_empty_when_server_not_configured() -> None:
    settings = make_settings(
        mssql_auth_mode="windows",
        mssql_server="",
        mssql_database="ChildcareBenefit",
    )

    assert settings.sqlalchemy_database_uri == ""


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_settings(log_level="NOT_A_LEVEL")


def test_log_level_is_normalized_to_uppercase() -> None:
    settings = make_settings(log_level="debug")

    assert settings.log_level == "DEBUG"
