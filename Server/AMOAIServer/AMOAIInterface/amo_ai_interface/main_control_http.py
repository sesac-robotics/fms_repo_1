"""Publish staff observations to the authenticated Main Control loopback API."""

import json
import logging
from http.client import HTTPConnection, RemoteDisconnected
from time import sleep
from urllib.parse import urlsplit


class MainControlWriter:
    """Send metadata only to the private, co-located observation endpoint."""

    def __init__(self, url: str, key: str) -> None:
        address = urlsplit(url)
        port = address.port
        if (
            address.scheme != 'http'
            or address.netloc != f'127.0.0.1:{port}'
            or not port
            or address.path != '/internal/vision/observations'
            or address.query
            or address.fragment
        ):
            raise ValueError('Main Control observations require an IPv4 loopback URL')
        if (
            len(key) < 32
            or not key.isascii()
            or not all(33 <= ord(c) <= 126 for c in key)
        ):
            raise ValueError(
                'Supply a dedicated printable ASCII Vision key of 32+ characters'
            )
        self._port = port
        self._key = key
        self._path = address.path

    def send(self, observation: dict[str, str | float]) -> None:
        """Send one observation, using the same encoded body on all attempts.

        Require HTTP 204. Retry once after a timeout, a dropped connection or a
        transient 5xx response. Never retry authorization or validation errors.
        """
        body = json.dumps(observation, allow_nan=False, separators=(',', ':')).encode()
        for attempt in range(2):
            try:
                status = self._post(body)
                if status == 204:
                    return
                if status not in (500, 502, 503, 504) or attempt == 1:
                    logging.warning('vision_observation_rejected status=%d', status)
                    raise ValueError(
                        f'Main Control rejected observation with HTTP {status}'
                    )
            except (TimeoutError, ConnectionError, RemoteDisconnected):
                if attempt == 1:
                    raise
            sleep(0.1)

    def _post(self, body: bytes) -> int:
        connection = HTTPConnection('127.0.0.1', self._port, timeout=1)
        try:
            connection.request(
                'POST',
                self._path,
                body=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-AMO-Vision-Key': self._key,
                },
            )
            with connection.getresponse() as reply:
                return reply.status
        finally:
            connection.close()
