from anemiaiaback.capture.application.dto.capture_dto import (
    CaptureResult,
    CreateCaptureCommand,
)
from anemiaiaback.capture.application.validators import validate_capture_data
from anemiaiaback.capture.domain.entity.capture import Capture
from anemiaiaback.capture.domain.errors import PersistenceError
from anemiaiaback.capture.domain.ibucket.iimage_bucket import ImageBucket
from anemiaiaback.capture.domain.iprocessor.iconjunctiva_processor import (
    ConjunctivaProcessor,
)
from anemiaiaback.capture.domain.irepository.icapture_repository import (
    CaptureRepository,
)


class CreateCaptureUseCase:
    def __init__(
        self,
        processor: ConjunctivaProcessor,
        bucket: ImageBucket,
        repository: CaptureRepository,
    ) -> None:
        self._processor = processor
        self._bucket = bucket
        self._repository = repository

    def execute(self, command: CreateCaptureCommand) -> CaptureResult:
        validate_capture_data(command.dni, command.sex, command.age)
        segmented_png = self._processor.extract(command.image)
        image_reference = self._bucket.save_png(segmented_png)
        capture = Capture(
            id=None,
            image=image_reference,
            dni=command.dni,
            age=command.age,
            gender=command.sex,
        )
        try:
            saved = self._repository.add(capture)
            if saved.id is None:
                raise PersistenceError("Repository did not return a patient identity")
        except Exception:
            try:
                self._bucket.delete(image_reference)
            except Exception:
                # Cleanup is best effort and must not hide the persistence failure.
                pass
            raise
        return CaptureResult(**saved.__dict__)
