import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from anemiaiaback.capture.domain.errors import ConfigurationError
from anemiaiaback.internal.utils.settings import Settings
from anemiaiaback.api.api import create_app


def test_invalid_upload_limit_environment_fails_fast(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    with pytest.raises(ConfigurationError, match="Invalid service configuration"):
        create_app()


def test_default_request_limit_includes_multipart_overhead():
    settings = Settings(_env_file=None, max_upload_bytes=10 * 1024 * 1024, max_request_bytes=None)
    assert settings.max_request_bytes == settings.max_upload_bytes + 1024 * 1024


def test_builds_database_url_safely_with_special_character_password():
    settings = Settings(
        _env_file=None,
        db_host="db.example.test",
        db_port=5432,
        db_name="postgres",
        db_user="postgres",
        db_password="p@ss&word:/?#[]",
        db_sslmode="require",
    )
    url = settings.database_connection_url
    assert url.password == "p@ss&word:/?#[]"
    assert url.query["sslmode"] == "require"
    rendered = url.render_as_string(hide_password=False)
    assert "p@ss&word:/?#[]" not in rendered
    assert make_url(rendered).password == "p@ss&word:/?#[]"


def test_loads_separate_database_values_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DB_HOST=db.example.test\n"
        "DB_PORT=5433\n"
        "DB_NAME=captures\n"
        "DB_USER=service\n"
        "DB_PASSWORD=test-secret\n"
        "DB_SSLMODE=require\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert settings.db_host == "db.example.test"
    assert settings.db_port == 5433
    assert settings.db_name == "captures"
    assert settings.db_user == "service"
    assert settings.db_password.get_secret_value() == "test-secret"
    assert settings.database_connection_url.query["sslmode"] == "require"


@pytest.mark.parametrize("sslmode", ["disable", "allow", "prefer"])
def test_rejects_insecure_db_sslmode(sslmode):
    with pytest.raises(ValidationError, match="DB_SSLMODE"):
        Settings(_env_file=None, db_sslmode=sslmode)


def test_database_url_without_sslmode_inherits_secure_mode():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://service:test@db.example.test/captures",
        db_sslmode="verify-full",
    )
    assert settings.database_connection_url.query["sslmode"] == "verify-full"


@pytest.mark.parametrize("sslmode", ["disable", "allow", "prefer"])
def test_rejects_insecure_database_url_sslmode(sslmode):
    with pytest.raises(ValidationError, match="DATABASE_URL sslmode"):
        Settings(
            _env_file=None,
            database_url=(
                "postgresql+psycopg://service:test@db.example.test/captures"
                f"?sslmode={sslmode}"
            ),
        )


def test_database_url_preserves_explicit_secure_sslmode():
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql+psycopg://service:test@db.example.test/captures"
            "?sslmode=verify-ca"
        ),
    )
    assert settings.database_connection_url.query["sslmode"] == "verify-ca"


def test_s3_configuration_is_all_or_nothing():
    with pytest.raises(ValidationError, match="all S3_\\* values"):
        Settings(_env_file=None, s3_bucket="images")


def test_s3_secrets_are_masked_in_settings_repr():
    settings = Settings(
        _env_file=None,
        s3_endpoint="https://example.test/storage/v1/s3",
        s3_region="us-west-2",
        s3_bucket="images",
        s3_access_key_id="private-access",
        s3_secret_access_key="private-secret",
    )
    rendered = repr(settings)
    assert "private-access" not in rendered
    assert "private-secret" not in rendered


def test_api_key_is_required_and_masked():
    settings = Settings(
        _env_file=None,
        api_key="a-secure-test-key-with-more-than-32-characters",
    )
    assert "a-secure-test-key" not in repr(settings)
    assert settings.require_api_key().startswith("a-secure")


@pytest.mark.parametrize("api_key", [None, "short"])
def test_rejects_missing_or_short_api_key(api_key):
    settings = Settings(_env_file=None, api_key=api_key)
    with pytest.raises(ConfigurationError, match="at least 32"):
        settings.require_api_key()
