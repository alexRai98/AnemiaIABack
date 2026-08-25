import re

from anemiaiaback.capture.domain.errors import CaptureValidationError


def validate_capture_data(dni: str, sex: str, age: int) -> None:
    if re.fullmatch(r"[0-9]{8}", dni) is None:
        raise CaptureValidationError("DNI must contain exactly 8 numeric digits")
    if sex not in {"M", "F"}:
        raise CaptureValidationError("Sex must be M or F")
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        raise CaptureValidationError("Age must be an integer greater than or equal to 0")
