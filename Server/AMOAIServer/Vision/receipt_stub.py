"""Diagnostic Vision HTTP service that acknowledges received JPEG bytes."""

import argparse
import json
import logging
from functools import partial
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID

_SERVICES = {1: 'driving-perception', 2: 'traffic-rules', 3: 'direction-recognition'}
_MAX_JPEG_BYTES = 2 * 1024 * 1024


class _ReceiptHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, vision_id: int, **kwargs) -> None:
        self._vision_id = vision_id
        super().__init__(*args, **kwargs)

    def _reply(self, status: HTTPStatus, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            logging.info('vision_receipt_client_disconnected id=%d', self._vision_id)

    def do_GET(self) -> None:
        """Acknowledge liveness at /health only."""
        if self.path != '/health':
            self._reply(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
            return
        self._reply(HTTPStatus.OK, {'ok': True, 'service': _SERVICES[self._vision_id]})

    def do_POST(self) -> None:
        """Respond to /infer with metadata about a bounded, complete JPEG."""
        if self.path != '/infer':
            self._reply(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
            return
        try:
            self.connection.settimeout(3)
            frame_id, image = self._read_frame()
        except (ValueError, OSError):
            self._reply(HTTPStatus.BAD_REQUEST, {'error': 'invalid_camera_frame'})
            return
        self._reply(
            HTTPStatus.OK,
            {
                'frame_id': frame_id,
                'vision_id': self._vision_id,
                'service': _SERVICES[self._vision_id],
                'bytes_received': len(image),
                'sha256': sha256(image).hexdigest(),
                'mock': True,
            },
        )
        logging.info(
            'vision_receipt frame=%s service=%s bytes=%d',
            frame_id,
            _SERVICES[self._vision_id],
            len(image),
        )

    def _read_frame(self) -> tuple[str, bytes]:
        frame_id = UUID(hex=self.headers.get('X-Frame-Id', '')).hex
        size = int(self.headers.get('Content-Length', ''))
        if (
            self.headers.get('X-Vision-Id') != str(self._vision_id)
            or self.headers.get('Content-Type') != 'image/jpeg'
            or not 5 <= size <= _MAX_JPEG_BYTES
        ):
            raise ValueError('Invalid Vision receipt request')
        image = self.rfile.read(size)
        if (
            len(image) != size
            or not image.startswith(b'\xff\xd8\xff')
            or not image.endswith(b'\xff\xd9')
        ):
            raise ValueError('Invalid JPEG envelope')
        return frame_id, image

    def log_message(self, format: str, *args: object) -> None:
        """Suppress untrusted request lines and health probes in access logs."""


def receipt_server(host: str, port: int, vision_id: int) -> ThreadingHTTPServer:
    """Bind the requested address and return a caller-owned diagnostic server.

    Port 0 chooses an ephemeral port. Raise ValueError for an unknown service.
    """
    if vision_id not in _SERVICES:
        raise ValueError('Unknown Vision ID')
    return ThreadingHTTPServer(
        (host, port), partial(_ReceiptHandler, vision_id=vision_id)
    )


def main() -> int:
    """Serve one test receiver on IPv4 loopback until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vision-id', required=True, type=int, choices=_SERVICES)
    parser.add_argument('--port', required=True, type=int)
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65_535:
        parser.error('--port must be between 1 and 65535')
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        with receipt_server('127.0.0.1', arguments.port, arguments.vision_id) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
