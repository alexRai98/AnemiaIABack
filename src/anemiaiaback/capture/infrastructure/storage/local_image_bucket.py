from pathlib import Path
from uuid import uuid4

from anemiaiaback.capture.domain.errors import ConfigurationError, StorageError


class LocalImageBucket:
    def __init__(self, root: Path, project_root: Path) -> None:
        self._project_root = project_root.resolve()
        if root.is_absolute():
            raise ConfigurationError("Bucket directory must be relative to the project root")
        candidate = (self._project_root / root).resolve()
        try:
            relative = candidate.relative_to(self._project_root)
        except ValueError as exc:
            raise ConfigurationError("Bucket directory must stay inside the project root") from exc
        if not relative.parts:
            raise ConfigurationError("Bucket directory must not be the project root")
        self._root = candidate
        self._relative_root = relative
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError("Could not initialize image storage") from exc

    def save_png(self, image: bytes) -> str:
        if not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise StorageError("Image storage accepts encoded PNG data only")
        filename = f"{uuid4()}.png"
        destination = self._root / filename
        temporary = self._root / f".{filename}.tmp"
        try:
            temporary.write_bytes(image)
            temporary.replace(destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise StorageError("Could not store segmented image") from exc
        return (self._relative_root / filename).as_posix()

    def delete(self, storage_key: str) -> None:
        destination = (self._project_root / storage_key).resolve()
        if destination.parent != self._root:
            raise StorageError("Refusing to delete a file outside image storage")
        try:
            destination.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Could not delete segmented image") from exc
