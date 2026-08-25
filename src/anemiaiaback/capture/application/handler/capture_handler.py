from typing import Annotated, Protocol

from fastapi import Depends, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from anemiaiaback.capture.application.dto.capture_dto import (
    CaptureResponse,
    CreateCaptureCommand,
)
from anemiaiaback.capture.domain.errors import UploadTooLargeError
from anemiaiaback.internal.utils.settings import Settings


class CaptureService(Protocol):
    def execute(self, command: CreateCaptureCommand): ...


def get_capture_service(request: Request) -> CaptureService:
    startup_error = getattr(request.app.state, "startup_error", None)
    if startup_error is not None:
        raise startup_error
    return request.app.state.capture_service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def create_capture_handler(
    image: Annotated[UploadFile, File(description="JPG or PNG eye image")],
    dni: Annotated[str, Form(pattern=r"^[0-9]{8}$")],
    sex: Annotated[str, Form(pattern=r"^[MF]$")],
    age: Annotated[int, Form(ge=0)],
    service: Annotated[CaptureService, Depends(get_capture_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CaptureResponse:
    image_bytes = await image.read(settings.max_upload_bytes + 1)
    if len(image_bytes) > settings.max_upload_bytes:
        raise UploadTooLargeError("Uploaded image exceeds the allowed size")
    result = await run_in_threadpool(
        service.execute,
        CreateCaptureCommand(image=image_bytes, dni=dni, sex=sex, age=age),
    )
    return CaptureResponse.model_validate(result.__dict__)
