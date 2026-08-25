from typing import Protocol


class ConjunctivaProcessor(Protocol):
    def extract(self, image: bytes) -> bytes: ...
