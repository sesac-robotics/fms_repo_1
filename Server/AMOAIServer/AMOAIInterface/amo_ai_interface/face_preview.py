"""Mask detected faces and retain road detail for the local operator preview."""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy import uint8
    from numpy.typing import NDArray

PREVIEW_MAGIC = b'AMOV2'
Rect = tuple[int, int, int, int]
_CASCADES = Path('/usr/share/opencv4/haarcascades')


def mask_regions(image: 'NDArray[uint8]', rectangles: list[Rect]) -> int:
    """Fill detected face boxes plus a 35% margin, in source-image pixels."""
    height, width = image.shape[:2]
    regions: list[Rect] = []
    for x, y, w, h in rectangles:
        if w <= 0 or h <= 0:
            raise ValueError('Invalid detector rectangle')
        dx, dy = (35 * w + 99) // 100, (35 * h + 99) // 100
        region = (
            max(0, x - dx),
            max(0, y - dy),
            min(width, x + w + dx),
            min(height, y + h + dy),
        )
        left, top, right, bottom = region
        if left >= right or top >= bottom:
            raise ValueError('Detector rectangle is outside the image')
        if region not in regions:
            regions.append(region)
    if len(regions) > 255:
        raise ValueError('Too many face regions for an operator preview')
    for left, top, right, bottom in regions:
        image[top:bottom, left:right] = 0
    return len(regions)


def load_face_masker() -> Callable[[bytes], bytes]:
    """Load local OpenCV models and return a fail-closed JPEG preview encoder."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError('Local preview requires OpenCV and NumPy') from exc

    if not hasattr(cv2, 'CascadeClassifier'):
        raise ValueError('Local preview requires the OpenCV 4 cascade module')

    frontal = cv2.CascadeClassifier(
        str(_CASCADES / 'haarcascade_frontalface_default.xml')
    )
    profile = cv2.CascadeClassifier(str(_CASCADES / 'haarcascade_profileface.xml'))
    if frontal.empty() or profile.empty():
        raise ValueError('Local preview face models could not be loaded')

    def encode(jpeg: bytes) -> bytes:
        image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.shape != (480, 640, 3):
            raise ValueError('Local face preview expects a 640x480 color JPEG')
        gray = cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        settings = {'scaleFactor': 1.1, 'minNeighbors': 4, 'minSize': (24, 24)}
        faces: list[Rect] = [
            (int(x), int(y), int(w), int(h))
            for cascade in (frontal, profile)
            for x, y, w, h in cascade.detectMultiScale(gray, **settings)
        ]
        faces.extend(
            (640 - int(x) - int(w), int(y), int(w), int(h))
            for x, y, w, h in profile.detectMultiScale(cv2.flip(gray, 1), **settings)
        )
        count = mask_regions(image, faces)
        ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise ValueError('Could not encode masked preview')
        return PREVIEW_MAGIC + bytes([count]) + encoded.tobytes()

    return encode
