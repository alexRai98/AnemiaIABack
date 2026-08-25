import pytest

from anemiaiaback.capture.application.dto.capture_dto import CreateCaptureCommand
from anemiaiaback.capture.application.usecase.create_capture_use_case import CreateCaptureUseCase


class Processor:
    def extract(self, image: bytes) -> bytes:
        return b"\x89PNG\r\n\x1a\nencoded"


class Bucket:
    def __init__(self) -> None:
        self.deleted = []

    def save_png(self, image: bytes) -> str:
        return "s3://ImagesProcesed/image.png"

    def delete(self, path: str) -> None:
        self.deleted.append(path)


class Repository:
    def __init__(self, fail: bool = False, missing_id: bool = False) -> None:
        self.fail = fail
        self.missing_id = missing_id
        self.saved = None

    def add(self, capture):
        if self.fail:
            raise RuntimeError("database unavailable")
        self.saved = capture
        return type(capture)(
            id=None if self.missing_id else 12,
            image=capture.image,
            dni=capture.dni,
            age=capture.age,
            gender=capture.gender,
        )


def test_create_capture_orchestrates_processing_storage_and_persistence():
    bucket, repository = Bucket(), Repository()
    result = CreateCaptureUseCase(Processor(), bucket, repository).execute(
        CreateCaptureCommand(b"image", "12345678", "F", 31)
    )
    assert result.image == "s3://ImagesProcesed/image.png"
    assert result.dni == "12345678"
    assert repository.saved is not None
    assert bucket.deleted == []


def test_create_capture_deletes_image_when_repository_fails():
    bucket = Bucket()
    with pytest.raises(RuntimeError, match="database unavailable"):
        CreateCaptureUseCase(Processor(), bucket, Repository(fail=True)).execute(
            CreateCaptureCommand(b"image", "12345678", "M", 0)
        )
    assert bucket.deleted == ["s3://ImagesProcesed/image.png"]


def test_create_capture_deletes_image_when_repository_omits_identity():
    bucket = Bucket()
    with pytest.raises(Exception, match="patient identity"):
        CreateCaptureUseCase(
            Processor(), bucket, Repository(missing_id=True)
        ).execute(CreateCaptureCommand(b"image", "12345678", "M", 20))
    assert bucket.deleted == ["s3://ImagesProcesed/image.png"]
