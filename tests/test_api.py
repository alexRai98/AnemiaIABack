import pytest
from fastapi.testclient import TestClient

from anemiaiaback.capture.application.dto.capture_dto import CaptureResult
from anemiaiaback.capture.domain.errors import (
    ConfigurationError,
    EyeNotFoundError,
    InvalidImageError,
    PersistenceError,
    StorageError,
)
from anemiaiaback.internal.utils.settings import Settings
from anemiaiaback.api.api import create_app


TEST_API_KEY = "test-api-key-with-at-least-32-characters"


def make_settings(**overrides):
    return Settings(_env_file=None, api_key=TEST_API_KEY, **overrides)


class Service:
    def execute(self, command):
        return CaptureResult(
            id=42,
            image="s3://ImagesProcesed/test.png",
            dni=command.dni,
            age=command.age,
            gender=command.sex,
        )


def test_capture_rejects_invalid_form_values():
    with TestClient(create_app(Service(), make_settings())) as client:
        response = client.post(
            "/api/v1/captures",
            headers={"X-API-Key": TEST_API_KEY},
            files={"image": ("eye.jpg", b"data", "image/jpeg")},
            data={"dni": "123", "sex": "X", "age": "-1"},
        )
    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "detail": "The multipart form contains invalid fields",
    }


def test_capture_accepts_valid_multipart_form():
    with TestClient(create_app(Service(), make_settings())) as client:
        response = client.post(
            "/api/v1/captures",
            headers={"X-API-Key": TEST_API_KEY},
            files={"image": ("eye.jpg", b"data", "image/jpeg")},
            data={"dni": "12345678", "sex": "M", "age": "28"},
        )
    assert response.status_code == 201
    assert response.json() == {
        "id": 42,
        "image": "s3://ImagesProcesed/test.png",
        "dni": "12345678",
        "age": 28,
        "gender": "M",
    }


def test_capture_limits_upload_without_unbounded_read():
    settings = make_settings(max_upload_bytes=4)
    with TestClient(create_app(Service(), settings)) as client:
        response = client.post(
            "/api/v1/captures",
            headers={"X-API-Key": TEST_API_KEY},
            files={"image": ("eye.jpg", b"12345", "image/jpeg")},
            data={"dni": "12345678", "sex": "M", "age": "28"},
        )
    assert response.status_code == 413
    assert response.json()["code"] == "image_too_large"


class FailingService:
    def __init__(self, error):
        self.error = error

    def execute(self, _command):
        raise self.error


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (InvalidImageError("private decoder detail"), 400, "invalid_image"),
        (EyeNotFoundError("private processing detail"), 422, "eye_not_found"),
        (ConfigurationError("private config path"), 500, "service_configuration_error"),
        (StorageError("private filesystem detail"), 500, "storage_error"),
        (PersistenceError("private database detail"), 503, "database_unavailable"),
    ],
)
def test_capture_maps_errors_without_leaking_internal_details(error, status_code, code):
    with TestClient(create_app(FailingService(error), make_settings())) as client:
        response = client.post(
            "/api/v1/captures",
            headers={"X-API-Key": TEST_API_KEY},
            files={"image": ("eye.jpg", b"data", "image/jpeg")},
            data={"dni": "12345678", "sex": "F", "age": "30"},
        )
    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert "private" not in response.json()["detail"]


def test_configuration_error_during_lifespan_fails_startup(monkeypatch):
    from anemiaiaback.api import api as api_module

    monkeypatch.setattr(api_module, "build_session_factory", lambda _url: object())

    def invalid_bucket(*_args, **_kwargs):
        raise ConfigurationError("invalid bucket configuration")

    monkeypatch.setattr(api_module, "SupabaseS3ImageBucket", invalid_bucket)
    settings = Settings(
        _env_file=None,
        s3_endpoint="https://example.test/storage/v1/s3",
        s3_region="us-west-2",
        s3_bucket="images",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        api_key=TEST_API_KEY,
    )
    with pytest.raises(ConfigurationError, match="invalid bucket configuration"):
        with TestClient(create_app(settings=settings)):
            pass


def test_missing_s3_configuration_fails_startup(monkeypatch):
    from anemiaiaback.api import api as api_module

    monkeypatch.setattr(api_module, "build_session_factory", lambda _url: object())
    with pytest.raises(ConfigurationError, match="S3 configuration is required"):
        with TestClient(create_app(settings=make_settings())):
            pass


def test_operational_persistence_error_produces_degraded_health(monkeypatch):
    from anemiaiaback.api import api as api_module

    def unavailable_database(_url):
        raise PersistenceError("database unavailable")

    monkeypatch.setattr(api_module, "build_session_factory", unavailable_database)
    with TestClient(create_app(settings=make_settings())) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "degraded"}


def test_capture_requires_valid_api_key():
    with TestClient(create_app(Service(), make_settings())) as client:
        missing = client.post("/api/v1/captures")
        invalid = client.post(
            "/api/v1/captures", headers={"X-API-Key": "wrong-key"}
        )
    expected = {
        "code": "unauthorized",
        "detail": "A valid API key is required",
    }
    assert missing.status_code == 401
    assert missing.json() == expected
    assert invalid.status_code == 401
    assert invalid.json() == expected


def test_health_and_docs_are_public():
    with TestClient(create_app(Service(), make_settings())) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200
