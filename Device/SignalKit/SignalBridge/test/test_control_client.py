"""Contract tests for the Main Control HTTP adapter against a local stub."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from amode_signal_bridge.control_client import (
    KEY_HEADER,
    ControlClient,
    ControlUnavailable,
    QueuedCommand,
)

KEY = 'k' * 32


class Stub(BaseHTTPRequestHandler):
    """Answers like Main Control and records what it received."""

    seen: list[tuple[str, str, str | None, bytes]] = []
    claim_status = 200
    claim_body = b'[{"id": 3, "signalId": "SIG-01", "command": "AUTO"}]'

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        body = self.rfile.read(int(self.headers['Content-Length']))
        self.seen.append(('POST', self.path, self.headers[KEY_HEADER], body))
        self.send_response(204 if self.headers[KEY_HEADER] == KEY else 401)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        self.seen.append(('GET', self.path, self.headers[KEY_HEADER], b''))
        self.send_response(self.claim_status)
        self.end_headers()
        self.wfile.write(self.claim_body)

    def log_message(self, *_args: object) -> None:
        pass


@pytest.fixture
def base_url() -> Iterator[str]:
    Stub.seen = []
    Stub.claim_status = 200
    server = HTTPServer(('127.0.0.1', 0), Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()


def test_posts_the_state_with_the_machine_key(base_url: str) -> None:
    client = ControlClient(base_url, KEY)
    assert client.post_state({'signalId': 'SIG-01', 'seq': 1}) == 204
    method, path, key, body = Stub.seen[0]
    assert (method, path, key) == ('POST', '/internal/signals/state', KEY)
    assert json.loads(body) == {'signalId': 'SIG-01', 'seq': 1}


def test_returns_http_errors_instead_of_raising(base_url: str) -> None:
    assert ControlClient(base_url, 'x' * 32).post_state({}) == 401


def test_claims_commands_in_order(base_url: str) -> None:
    client = ControlClient(base_url, KEY)
    assert client.claim_commands('SIG-01') == [QueuedCommand(3, 'AUTO')]
    assert Stub.seen[0][:3] == ('GET', '/internal/signals/SIG-01/commands', KEY)


def test_claim_failures_raise(base_url: str) -> None:
    client = ControlClient(base_url, KEY)
    Stub.claim_status = 503
    with pytest.raises(ControlUnavailable):
        client.claim_commands('SIG-01')


def test_unreachable_server_raises() -> None:
    client = ControlClient('http://127.0.0.1:9', KEY, timeout_s=0.5)
    with pytest.raises(ControlUnavailable):
        client.post_state({})


def test_rejects_a_short_key() -> None:
    with pytest.raises(ValueError):
        ControlClient('http://127.0.0.1:1', 'short')
