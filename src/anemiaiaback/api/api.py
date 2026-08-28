from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from anemiaiaback.api.routes import router
from anemiaiaback.capture.application.handler.capture_handler import CaptureService
from anemiaiaback.capture.application.usecase.create_capture_use_case import (
    CreateCaptureUseCase,
)
from anemiaiaback.capture.domain.errors import (
    CaptureValidationError,
    ConfigurationError,
    ConjunctivaContourNotFoundError,
    EyeNotFoundError,
    InvalidConjunctivaCropError,
    InvalidImageError,
    IrisNotFoundError,
    PersistenceError,
    StorageError,
    UploadTooLargeError,
)
from anemiaiaback.capture.infrastructure.processing.opencv_conjunctiva_processor import (
    OpenCvConjunctivaProcessor,
)
from anemiaiaback.capture.infrastructure.storage.postgres_capture_repository import (
    SqlAlchemyCaptureRepository,
    build_session_factory,
)
from anemiaiaback.capture.infrastructure.storage.supabase_s3_image_bucket import (
    SupabaseS3ImageBucket,
)
from anemiaiaback.internal.middleware.api_key import APIKeyMiddleware
from anemiaiaback.internal.middleware.body_limit import RequestBodyLimitMiddleware
from anemiaiaback.internal.utils.settings import Settings


ERROR_MAPPING = {
    UploadTooLargeError: (413, "image_too_large", "The image exceeds the allowed size"),
    InvalidImageError: (400, "invalid_image", "The upload must be a decodable JPG or PNG image"),
    EyeNotFoundError: (422, "eye_not_found", "No eye was detected in the image"),
    IrisNotFoundError: (422, "iris_not_found", "No iris was detected in the image"),
    InvalidConjunctivaCropError: (422, "invalid_conjunctiva_crop", "The conjunctiva region could not be extracted"),
    ConjunctivaContourNotFoundError: (422, "conjunctiva_contour_not_found", "No conjunctiva contour was found"),
    ConfigurationError: (500, "service_configuration_error", "The service is not configured correctly"),
    StorageError: (500, "storage_error", "The image could not be stored"),
    PersistenceError: (503, "database_unavailable", "Capture data could not be persisted"),
    CaptureValidationError: (422, "validation_error", "Capture data is invalid"),
}


def _error(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def create_app(
    service: CaptureService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    try:
        resolved_settings = settings or Settings()
    except ValidationError:
        raise ConfigurationError(
            "Invalid service configuration; check environment values"
        ) from None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is None:
            try:
                repository = SqlAlchemyCaptureRepository(
                    build_session_factory(resolved_settings.database_connection_url)
                )
                endpoint, region, bucket_name, access_key, secret_key = (
                    resolved_settings.require_s3_configuration()
                )
                bucket = SupabaseS3ImageBucket(
                    endpoint_url=endpoint,
                    region=region,
                    bucket=bucket_name,
                    access_key_id=access_key,
                    secret_access_key=secret_key,
                )
                app.state.capture_service = CreateCaptureUseCase(
                    OpenCvConjunctivaProcessor(
                        max_pixels=resolved_settings.max_image_pixels
                    ),
                    bucket,
                    repository,
                )
            except (StorageError, PersistenceError) as exc:
                app.state.startup_error = exc
        yield

    app = FastAPI(title="AnemiaIA API", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.capture_service = service
    app.state.startup_error = None
    
    # CORS middleware - permite acceso desde dispositivos en la red local
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especifica los orígenes permitidos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_request_bytes=resolved_settings.max_request_bytes,
    )
    app.add_middleware(
        APIKeyMiddleware,
        api_key=resolved_settings.require_api_key(),
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "degraded"
            if getattr(app.state, "startup_error", None) is not None
            else "ok"
        }

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _: Request, __: RequestValidationError
    ) -> JSONResponse:
        return _error(422, "validation_error", "The multipart form contains invalid fields")

    for error_type, (status_code, code, detail) in ERROR_MAPPING.items():
        async def handler(
            _: Request,
            __: Exception,
            status_code: int = status_code,
            code: str = code,
            detail: str = detail,
        ) -> JSONResponse:
            return _error(status_code, code, detail)

        app.add_exception_handler(error_type, handler)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        return _error(500, "internal_error", "An unexpected error occurred")

    app.include_router(router)
    return app


app = create_app()
