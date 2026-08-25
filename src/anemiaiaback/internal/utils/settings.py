from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

from anemiaiaback.capture.domain.errors import ConfigurationError


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})


class Settings(BaseSettings):
    api_key: SecretStr | None = None
    db_host: str = "localhost"
    db_port: int = Field(default=5432, gt=0, le=65535)
    db_name: str = "AnemiaIA"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")
    db_sslmode: str = "require"
    database_url: SecretStr | None = None
    s3_endpoint: str | None = None
    s3_region: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_request_bytes: int | None = Field(default=None, gt=0)
    max_image_pixels: int = Field(default=24_000_000, gt=0)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_connection_url(self) -> URL:
        if self.database_url:
            url = make_url(self.database_url.get_secret_value())
            if "sslmode" not in url.query:
                return url.update_query_dict({"sslmode": self.db_sslmode})
            return url
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if self.db_sslmode not in SECURE_SSL_MODES:
            raise ValueError(
                "DB_SSLMODE must be require, verify-ca, or verify-full"
            )
        if self.database_url:
            database_url = make_url(self.database_url.get_secret_value())
            url_sslmode = database_url.query.get("sslmode")
            if url_sslmode is not None and url_sslmode not in SECURE_SSL_MODES:
                raise ValueError(
                    "DATABASE_URL sslmode must be require, verify-ca, or verify-full"
                )
        s3_values = (
            self.s3_endpoint,
            self.s3_region,
            self.s3_bucket,
            self.s3_access_key_id.get_secret_value()
            if self.s3_access_key_id is not None
            else None,
            self.s3_secret_access_key.get_secret_value()
            if self.s3_secret_access_key is not None
            else None,
        )
        if any(value is not None for value in s3_values) and not all(
            value is not None and value.strip() for value in s3_values
        ):
            raise ValueError("S3 configuration must provide all S3_* values")
        if self.s3_endpoint is not None and not self.s3_endpoint.startswith("https://"):
            raise ValueError("S3_ENDPOINT must use HTTPS")
        if self.max_request_bytes is None:
            self.max_request_bytes = self.max_upload_bytes + 1024 * 1024
        if self.max_request_bytes < self.max_upload_bytes:
            raise ValueError("MAX_REQUEST_BYTES must be at least MAX_UPLOAD_BYTES")
        return self

    def require_s3_configuration(self) -> tuple[str, str, str, str, str]:
        access_key = (
            self.s3_access_key_id.get_secret_value()
            if self.s3_access_key_id is not None
            else ""
        )
        secret_key = (
            self.s3_secret_access_key.get_secret_value()
            if self.s3_secret_access_key is not None
            else ""
        )
        if not all(
            value and value.strip()
            for value in (
                self.s3_endpoint,
                self.s3_region,
                self.s3_bucket,
                access_key,
                secret_key,
            )
        ):
            raise ConfigurationError("S3 configuration is required")
        return (
            self.s3_endpoint,
            self.s3_region,
            self.s3_bucket,
            access_key,
            secret_key,
        )

    def require_api_key(self) -> str:
        api_key = self.api_key.get_secret_value() if self.api_key is not None else ""
        if len(api_key) < 32:
            raise ConfigurationError("API_KEY must contain at least 32 characters")
        return api_key
