"""Find a barcode or QR code in a photo."""

import cv2
import numpy as np
from pyzbar import pyzbar


def decode_image(image_bytes: bytes) -> str | None:
    """Return the text of the first barcode/QR code in the image, or None."""
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Not a valid image")

    # Low-cost cameras give small or blurry photos, so try a few cleaned-up
    # versions of the image before giving up.
    for variant in _variants(img):
        found = pyzbar.decode(variant)
        if found:
            return found[0].data.decode("utf-8", errors="replace")
    return None


def _variants(img: np.ndarray):
    yield img
    yield cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    yield cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    yield cv2.filter2D(img, -1, sharpen)
