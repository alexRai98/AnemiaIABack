from typing import Protocol

from anemiaiaback.capture.domain.entity.capture import Capture


class CaptureRepository(Protocol):
    def add(self, capture: Capture) -> Capture: ...
