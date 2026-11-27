"""HTTP adapter for Main Control's internal signal endpoints.

Uses only the standard library. Every request carries the machine key in
``X-AMO-Signal-Key`` and is bounded by ``timeout_s``. Transport failures raise
``ControlUnavailable``; HTTP error statuses are returned to the caller.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

KEY_HEADER = 'X-AMO-Signal-Key'


class ControlUnavailable(Exception):
    """Main Control could not be reached or answered with an unusable body."""


@dataclass(frozen=True)
class QueuedCommand:
    """A staff command claimed from the queue."""

    id: int
    command: str


class ControlClient:
    """Calls POST /internal/signals/state and GET /internal/signals/{id}/commands."""

    def __init__(self, base_url: str, key: str, timeout_s: float = 1.0) -> None:
        """Use ``base_url`` such as http://127.0.0.1:18088 and a 32+ character key."""
        if len(key) < 32:
            raise ValueError('the signal ingest key must have at least 32 characters')
        self._base = base_url.rstrip('/')
        self._key = key
        self._timeout_s = timeout_s

    def post_state(self, document: dict[str, object]) -> int:
        """Send one firmware state document; return the HTTP status (204 when stored)."""
        body = json.dumps(document).encode()
        return self._send('POST', '/internal/signals/state', body)[0]

    def claim_commands(self, signal_id: str) -> list[QueuedCommand]:
        """Claim the signal's undelivered commands, oldest first.

        Raises ControlUnavailable for a non-200 status or a malformed body,
        because claimed commands must not be dropped silently.
        """
        status, payload = self._send('GET', f'/internal/signals/{signal_id}/commands')
        if status != 200:
            raise ControlUnavailable(f'claim returned HTTP {status}')
        try:
            rows = json.loads(payload or b'[]')
            return [QueuedCommand(int(row['id']), str(row['command'])) for row in rows]
        except (ValueError, KeyError, TypeError) as error:
            raise ControlUnavailable('claim returned an invalid body') from error

    def _send(
        self, method: str, path: str, body: bytes | None = None
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(self._base + path, data=body, method=method)
        request.add_header(KEY_HEADER, self._key)
        if body is not None:
            request.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as failure:
            return failure.code, failure.read()
        except (urllib.error.URLError, OSError) as failure:
            raise ControlUnavailable(str(failure)) from failure
