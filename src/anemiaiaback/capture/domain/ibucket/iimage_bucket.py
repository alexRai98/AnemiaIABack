from typing import Protocol


class ImageBucket(Protocol):
    def save_png(self, image: bytes) -> str: ...

    def delete(self, storage_key: str) -> None: ...
