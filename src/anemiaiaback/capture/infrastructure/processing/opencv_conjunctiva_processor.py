from pathlib import Path

import cv2
import numpy as np

from anemiaiaback.capture.domain.errors import (
    ConjunctivaContourNotFoundError,
    ConfigurationError,
    EyeNotFoundError,
    InvalidConjunctivaCropError,
    InvalidImageError,
    IrisNotFoundError,
    UploadTooLargeError,
)


class OpenCvConjunctivaProcessor:
    """Adaptation of 4_FINAL_CANAL_ROJO_VERDE_MAPA_ROJEZ.py for one image."""

    REDNESS_WEIGHT = 0.55
    RED_CHANNEL_WEIGHT = 0.45
    SEGMENTATION_BLUR_KERNEL = (11, 11)

    def __init__(self, cascade_path: Path | None = None, max_pixels: int = 24_000_000) -> None:
        default = Path(__file__).resolve().parents[1] / "resources" / "haarcascade_eye.xml"
        self._cascade_path = cascade_path or default
        self._max_pixels = max_pixels

    def extract(self, image: bytes) -> bytes:
        encoded_width, encoded_height = self._encoded_dimensions(image)
        if encoded_width * encoded_height > self._max_pixels:
            raise UploadTooLargeError("Encoded image dimensions exceed the allowed pixel count")
        original = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if original is None or original.size == 0:
            raise InvalidImageError("Image is not a decodable JPG or PNG")
        if original.shape[0] * original.shape[1] > self._max_pixels:
            raise UploadTooLargeError("Decoded image exceeds the allowed pixel count")

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        green = clahe.apply(original[:, :, 1])
        red = clahe.apply(original[:, :, 2])

        cascade = cv2.CascadeClassifier(str(self._cascade_path))
        if cascade.empty():
            raise ConfigurationError("Eye detection model could not be loaded")
        eyes = cascade.detectMultiScale(
            red, scaleFactor=1.01, minNeighbors=7, minSize=(650, 650)
        )
        if len(eyes) == 0:
            raise EyeNotFoundError("No eye was detected")

        x, y, w, h = self._select_central_eye(eyes, original.shape[1], original.shape[0])
        margin_w, margin_h = int(w * 0.15), int(h * 0.15)
        x_m, y_m = max(0, x - margin_w), max(0, y - margin_h)
        w_m = min(original.shape[1] - x_m, w + 2 * margin_w)
        h_m = min(original.shape[0] - y_m, h + 2 * margin_h)
        roi_color = original[y_m : y_m + h_m, x_m : x_m + w_m].copy()
        roi_green = green[y_m : y_m + h_m, x_m : x_m + w_m].copy()

        blurred_green = cv2.GaussianBlur(roi_green, (19, 19), 0)
        _, threshold_green = cv2.threshold(
            blurred_green, 69, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV
        )
        circles = cv2.HoughCircles(
            threshold_green,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=h_m // 2,
            param1=100,
            param2=10,
            minRadius=int(h_m / 12),
            maxRadius=int(h_m / 6),
        )
        if circles is None or len(circles[0]) == 0:
            raise IrisNotFoundError("No iris was detected")

        center = (w_m // 2, h_m // 2)
        circle = min(
            np.around(circles[0]).astype(int),
            key=lambda c: ((int(c[0]) - center[0]) ** 2 + (int(c[1]) - center[1]) ** 2, int(c[2])),
        )
        cx, cy, radius = map(int, circle)
        y_start, y_end = cy + int(radius * 1.3), cy + int(radius * 3.1)
        x_start, x_end = cx - int(radius * 1.5), cx + int(radius * 1.5)
        if not (0 <= y_start < y_end < h_m and 0 < x_start < x_end < w_m):
            raise InvalidConjunctivaCropError("Detected iris produces an invalid conjunctiva crop")

        conjunctiva = roi_color[y_start:y_end, x_start:x_end].copy()
        roi_red = red[y_m : y_m + h_m, x_m : x_m + w_m]
        conjunctiva_red = roi_red[y_start:y_end, x_start:x_end].copy()
        if conjunctiva.size == 0 or conjunctiva_red.size == 0:
            raise InvalidConjunctivaCropError("Conjunctiva crop is empty")
        segmented = self._segment(conjunctiva, conjunctiva_red)
        encoded, png = cv2.imencode(".png", segmented)
        if not encoded:
            raise InvalidImageError("Segmented conjunctiva could not be encoded")
        return png.tobytes()

    @staticmethod
    def _encoded_dimensions(image: bytes) -> tuple[int, int]:
        if image.startswith(b"\x89PNG\r\n\x1a\n"):
            if len(image) < 24 or image[12:16] != b"IHDR":
                raise InvalidImageError("PNG header is malformed")
            width = int.from_bytes(image[16:20], "big")
            height = int.from_bytes(image[20:24], "big")
            if width <= 0 or height <= 0:
                raise InvalidImageError("PNG dimensions are invalid")
            return width, height
        if image.startswith(b"\xff\xd8"):
            return OpenCvConjunctivaProcessor._jpeg_dimensions(image)
        raise InvalidImageError("Image must be a JPG or PNG file")

    @staticmethod
    def _jpeg_dimensions(image: bytes) -> tuple[int, int]:
        sof_markers = {
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        }
        position = 2
        while position < len(image):
            if image[position] != 0xFF:
                raise InvalidImageError("JPEG marker stream is malformed")
            while position < len(image) and image[position] == 0xFF:
                position += 1
            if position >= len(image):
                break
            marker = image[position]
            position += 1
            if marker in {0xD9, 0xDA}:
                break
            if marker == 0x01 or 0xD0 <= marker <= 0xD7:
                continue
            if position + 2 > len(image):
                raise InvalidImageError("JPEG segment length is missing")
            segment_length = int.from_bytes(image[position : position + 2], "big")
            if segment_length < 2 or position + segment_length > len(image):
                raise InvalidImageError("JPEG segment is malformed")
            if marker in sof_markers:
                if segment_length < 7:
                    raise InvalidImageError("JPEG SOF segment is malformed")
                height = int.from_bytes(image[position + 3 : position + 5], "big")
                width = int.from_bytes(image[position + 5 : position + 7], "big")
                if width <= 0 or height <= 0:
                    raise InvalidImageError("JPEG dimensions are invalid")
                return width, height
            position += segment_length
        raise InvalidImageError("JPEG dimensions could not be read")

    @staticmethod
    def _select_central_eye(eyes: np.ndarray, width: int, height: int) -> tuple[int, int, int, int]:
        """Choose one result: closest to center, then largest, topmost, leftmost."""
        image_center = np.array([width / 2, height / 2])
        selected = min(
            eyes,
            key=lambda eye: (
                float(np.linalg.norm(np.array([eye[0] + eye[2] / 2, eye[1] + eye[3] / 2]) - image_center)),
                -int(eye[2] * eye[3]),
                int(eye[1]),
                int(eye[0]),
            ),
        )
        return tuple(map(int, selected))

    @staticmethod
    def _segment(conjunctiva: np.ndarray, conjunctiva_red: np.ndarray) -> np.ndarray:
        fusion = OpenCvConjunctivaProcessor._hybrid_fusion(conjunctiva, conjunctiva_red)
        blurred = cv2.GaussianBlur(
            fusion, OpenCvConjunctivaProcessor.SEGMENTATION_BLUR_KERNEL, 0
        )
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ConjunctivaContourNotFoundError("No conjunctiva contour was found")
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) <= 0:
            raise ConjunctivaContourNotFoundError("No valid conjunctiva contour was found")
        mask = np.zeros(otsu.shape, dtype=np.uint8)
        cv2.drawContours(mask, [largest], -1, 255, -1)
        return cv2.bitwise_and(conjunctiva, conjunctiva, mask=mask)

    @staticmethod
    def _hybrid_fusion(conjunctiva: np.ndarray, conjunctiva_red: np.ndarray) -> np.ndarray:
        red_norm = cv2.normalize(conjunctiva_red, None, 0, 255, cv2.NORM_MINMAX)
        blue, green, red = cv2.split(conjunctiva)
        redness = cv2.subtract(red, cv2.max(green, blue))
        redness_norm = cv2.normalize(redness, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.addWeighted(
            redness_norm,
            OpenCvConjunctivaProcessor.REDNESS_WEIGHT,
            red_norm,
            OpenCvConjunctivaProcessor.RED_CHANNEL_WEIGHT,
            0,
        )
