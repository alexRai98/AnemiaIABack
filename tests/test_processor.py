import cv2
import hashlib
import numpy as np
import pytest

from anemiaiaback.capture.infrastructure.processing.opencv_conjunctiva_processor import OpenCvConjunctivaProcessor
from anemiaiaback.capture.domain.errors import InvalidImageError, UploadTooLargeError


def test_rejects_non_image_bytes():
    with pytest.raises(InvalidImageError):
        OpenCvConjunctivaProcessor().extract(b"not-an-image")


def test_hybrid_segmentation_keeps_only_largest_red_region():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (50, 60), (20, 20, 220), -1)
    cv2.rectangle(image, (75, 75), (85, 85), (20, 20, 200), -1)
    result = OpenCvConjunctivaProcessor._segment(image, image[:, :, 2])
    assert result[30, 30, 2] > 0
    assert result[80, 80].sum() == 0


def test_hybrid_segmentation_matches_independent_thesis_reference():
    # This fixture deliberately makes the normalized CLAHE-red input favor the
    # right region while the normalized R-max(G,B) map favors the larger left
    # region. It therefore detects swapped/changed 0.45/0.55 weights; a uniform
    # red fixture would make both normalized inputs equivalent and miss that bug.
    y, x = np.indices((96, 128))
    image = np.stack(
        (
            ((3 * x + 5 * y) % 70).astype(np.uint8),
            ((7 * x + 2 * y) % 90).astype(np.uint8),
            ((5 * x + 11 * y) % 120).astype(np.uint8),
        ),
        axis=2,
    )
    image[10:82, 8:60] = (15, 25, 230)
    image[18:76, 72:122] = (65, 75, 115)
    clahe_red = ((17 * x + 3 * y) % 80).astype(np.uint8)
    clahe_red[10:82, 8:60] = 75
    clahe_red[18:76, 72:122] = 245

    # Independent transcription of the thesis script's fixed segmentation
    # equations: normalized redness * .55 + normalized red * .45, Gaussian
    # (11,11), Otsu, then the largest external contour.
    red_norm = cv2.normalize(clahe_red, None, 0, 255, cv2.NORM_MINMAX)
    blue, green, red = cv2.split(image)
    redness_norm = cv2.normalize(
        cv2.subtract(red, cv2.max(green, blue)), None, 0, 255, cv2.NORM_MINMAX
    )
    assert not np.array_equal(red_norm, redness_norm)
    reference_fusion = cv2.addWeighted(redness_norm, 0.55, red_norm, 0.45, 0)
    reference_blur = cv2.GaussianBlur(reference_fusion, (11, 11), 0)
    _, reference_otsu = cv2.threshold(reference_blur, 0, 255, cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(
        reference_otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    reference_mask = np.zeros(reference_otsu.shape, dtype=np.uint8)
    cv2.drawContours(reference_mask, [max(contours, key=cv2.contourArea)], -1, 255, -1)
    expected = cv2.bitwise_and(image, image, mask=reference_mask)

    processor_fusion = OpenCvConjunctivaProcessor._hybrid_fusion(image, clahe_red)
    result = OpenCvConjunctivaProcessor._segment(image, clahe_red)
    assert OpenCvConjunctivaProcessor.REDNESS_WEIGHT == 0.55
    assert OpenCvConjunctivaProcessor.RED_CHANNEL_WEIGHT == 0.45
    assert OpenCvConjunctivaProcessor.SEGMENTATION_BLUR_KERNEL == (11, 11)
    assert np.array_equal(processor_fusion, reference_fusion)
    assert hashlib.sha256(result.tobytes()).digest() == hashlib.sha256(
        expected.tobytes()
    ).digest()
    assert np.array_equal(result, expected)


def test_eye_selection_is_central_then_largest_topmost_leftmost():
    eyes = np.array([
        [100, 400, 100, 100],
        [400, 100, 100, 100],
        [350, 350, 300, 300],
        [375, 375, 250, 250],
    ])
    assert OpenCvConjunctivaProcessor._select_central_eye(eyes, 1000, 1000) == (350, 350, 300, 300)

    tied = np.array([[600, 400, 100, 100], [300, 400, 100, 100]])
    assert OpenCvConjunctivaProcessor._select_central_eye(tied, 1000, 1000) == (300, 400, 100, 100)


def test_full_pipeline_returns_encoded_segmented_png(monkeypatch):
    class Cascade:
        def empty(self):
            return False

        def detectMultiScale(self, *_args, **_kwargs):
            return np.array([[100, 100, 700, 700], [250, 250, 650, 650]])

    monkeypatch.setattr(cv2, "CascadeClassifier", lambda *_: Cascade())
    monkeypatch.setattr(
        cv2,
        "HoughCircles",
        lambda *_args, **_kwargs: np.array([[[455.0, 300.0, 80.0]]], dtype=np.float32),
    )
    eye = np.zeros((1000, 1000, 3), dtype=np.uint8)
    cv2.rectangle(eye, (335, 404), (575, 548), (20, 40, 220), -1)
    cv2.circle(eye, (455, 470), 35, (10, 20, 255), -1)
    ok, encoded = cv2.imencode(".jpg", eye)
    assert ok
    result = OpenCvConjunctivaProcessor().extract(encoded.tobytes())
    assert result.startswith(b"\x89PNG\r\n\x1a\n")
    decoded = cv2.imdecode(np.frombuffer(result, np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None and decoded.any()
    assert decoded.shape == (144, 240, 3)


def test_rejects_decoded_image_over_pixel_limit():
    ok, encoded = cv2.imencode(".png", np.zeros((20, 20, 3), dtype=np.uint8))
    assert ok
    with pytest.raises(UploadTooLargeError):
        OpenCvConjunctivaProcessor(max_pixels=100).extract(encoded.tobytes())


def test_rejects_huge_png_dimensions_before_decode():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (100_000).to_bytes(4, "big") * 2
    with pytest.raises(UploadTooLargeError):
        OpenCvConjunctivaProcessor(max_pixels=1_000_000).extract(png)


def test_rejects_huge_jpeg_dimensions_before_decode():
    jpeg = (
        b"\xff\xd8\xff\xc0\x00\x0b\x08"
        + (65_535).to_bytes(2, "big")
        + (65_535).to_bytes(2, "big")
        + b"\x01\x01\x11\x00"
    )
    with pytest.raises(UploadTooLargeError):
        OpenCvConjunctivaProcessor(max_pixels=1_000_000).extract(jpeg)
