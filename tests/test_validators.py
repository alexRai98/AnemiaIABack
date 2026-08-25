import pytest

from anemiaiaback.capture.application.validators import validate_capture_data
from anemiaiaback.capture.domain.errors import CaptureValidationError


@pytest.mark.parametrize("dni", ["123", "1234567a", "123456789"])
def test_rejects_invalid_dni(dni):
    with pytest.raises(CaptureValidationError, match="DNI"):
        validate_capture_data(dni, "M", 20)


@pytest.mark.parametrize("sex", ["m", "X", ""])
def test_rejects_invalid_sex(sex):
    with pytest.raises(CaptureValidationError, match="Sex"):
        validate_capture_data("12345678", sex, 20)


def test_rejects_negative_age():
    with pytest.raises(CaptureValidationError, match="Age"):
        validate_capture_data("12345678", "F", -1)
