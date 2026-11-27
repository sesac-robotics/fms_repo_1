"""HTTP adapter for diagnostic and detector-mode Vision endpoints."""

import json
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPConnection
from urllib.parse import urlsplit

from amo_ai_interface.frame import Frame

SERVICES = {1: 'driving-perception', 2: 'traffic-rules', 3: 'direction-recognition'}
HTTP_TIMEOUT_SECONDS = 3
_MAX_RESPONSE_BYTES = 4096


@dataclass(frozen=True, slots=True)
class VisionTarget:
    """One named Vision service with an explicit HTTP endpoint."""

    vision_id: int
    endpoint: str

    @property
    def service(self) -> str:
        """Return the service name for this configured receipt ID."""
        return SERVICES[self.vision_id]

    def __post_init__(self) -> None:
        """Reject unsupported IDs, credentials, or paths other than /infer."""
        url = urlsplit(self.endpoint)
        if (
            self.vision_id not in SERVICES
            or url.scheme != 'http'
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or url.path != '/infer'
            or url.port == 0
        ):
            raise ValueError('Expected a known Vision service and HTTP /infer URL')


def request_inference(target: VisionTarget, frame: Frame) -> object:
    """Send one JPEG and return its bounded JSON response.

    Close the connection on success and failure. Socket operations time out
    after three seconds. Propagate transport errors or malformed JSON.
    """
    url = urlsplit(target.endpoint)
    connection = HTTPConnection(
        url.hostname or '', url.port, timeout=HTTP_TIMEOUT_SECONDS
    )
    try:
        connection.request(
            'POST',
            '/infer',
            body=frame.jpeg,
            headers={
                'Content-Type': 'image/jpeg',
                'Accept': 'application/json',
                'X-Frame-Id': frame.frame_id,
                'X-Vision-Id': str(target.vision_id),
                'X-Robot-Id': frame.robot_id,
            },
        )
        with connection.getresponse() as response:
            if response.status != 200:
                raise ValueError(f'Vision returned HTTP {response.status}')
            if response.headers.get_content_type() != 'application/json':
                raise ValueError('Vision must return application/json')
            payload = response.read(_MAX_RESPONSE_BYTES + 1)
    finally:
        connection.close()

    if len(payload) > _MAX_RESPONSE_BYTES:
        raise ValueError('Vision JSON exceeds the response limit')
    try:
        return json.loads(payload)
    except RecursionError as error:
        raise ValueError('Vision JSON nesting exceeds the limit') from error


def confirm_receipt(target: VisionTarget, frame: Frame) -> None:
    """Require the exact diagnostic receipt for the transmitted JPEG."""
    receipt = request_inference(target, frame)
    expected = {
        'frame_id': frame.frame_id,
        'vision_id': target.vision_id,
        'service': target.service,
        'bytes_received': len(frame.jpeg),
        'sha256': sha256(frame.jpeg).hexdigest(),
        'mock': True,
    }
    if receipt != expected or any(
        type(receipt[key]) is not type(value) for key, value in expected.items()
    ):
        raise ValueError('Vision receipt does not match the transmitted JPEG')
