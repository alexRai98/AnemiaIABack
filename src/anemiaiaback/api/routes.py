from fastapi import APIRouter, status

from anemiaiaback.capture.application.dto.capture_dto import (
    CaptureResponse,
    ErrorResponse,
)
from anemiaiaback.capture.application.handler.capture_handler import (
    create_capture_handler,
)


router = APIRouter(prefix="/api/v1", tags=["captures"])
router.add_api_route(
    "/captures",
    create_capture_handler,
    methods=["POST"],
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
