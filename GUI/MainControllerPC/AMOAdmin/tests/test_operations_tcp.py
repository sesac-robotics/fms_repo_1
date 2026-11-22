"""Regression tests for the provisional IF-03 operations adapter."""

from __future__ import annotations

import json
import unittest
from base64 import b64encode
from typing import Any

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
from PyQt6.QtNetwork import QHostAddress, QTcpServer

from amo_fms.operations_tcp import (
    MAX_FRAME_BYTES,
    OperationsTcpRequest,
    snapshot_request,
    snapshot_response,
)


def _frame(message: dict[str, Any]) -> bytes:
    data = json.dumps(message).encode()
    return len(data).to_bytes(4, 'big') + data


class OperationsTcpTests(unittest.TestCase):
    """Validate framing and asynchronous delivery with a local fake server."""

    def test_request_has_read_only_path_and_bearer_header(self) -> None:
        request = snapshot_request('session-token')
        self.assertEqual(int.from_bytes(request[:4], 'big'), len(request) - 4)
        self.assertEqual(
            json.loads(request[4:]),
            {
                'method': 'GET',
                'path': '/api/operations',
                'headers': {
                    'Accept': ['application/json'],
                    'Authorization': ['Bearer session-token'],
                },
                'body': '',
            },
        )

    def test_rejects_invalid_lengths_and_payloads(self) -> None:
        for frame in (
            b'\0\0\0\0',
            (MAX_FRAME_BYTES + 1).to_bytes(4, 'big'),
            _frame({'status': 200, 'headers': {}, 'body': 'not base64!'}),
            _frame({'status': 200, 'headers': {}, 'body': 'e30='}) + b'extra',
        ):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                snapshot_response(frame)
        unauthorized = _frame({'status': 401, 'headers': {}, 'body': ''})
        self.assertEqual(snapshot_response(unauthorized), (401, None))

    def test_snapshot_round_trip_with_split_prefix(self) -> None:
        app = QCoreApplication.instance() or QCoreApplication([])
        self.assertIsNotNone(app)
        server = QTcpServer()
        self.assertTrue(server.listen(QHostAddress('127.0.0.1'), 0))
        loop = QEventLoop()
        received = bytearray()
        snapshot = {'demo': True, 'vehicles': [], 'requests': [], 'events': []}
        response = _frame(
            {
                'status': 200,
                'headers': {'Content-Type': ['application/json']},
                'body': b64encode(json.dumps(snapshot).encode()).decode(),
            }
        )
        sockets = []

        def accept() -> None:
            peer = server.nextPendingConnection()
            sockets.append(peer)

            def receive() -> None:
                received.extend(bytes(peer.readAll()))
                if bytes(received) == snapshot_request('session-token'):
                    peer.write(response[:2])
                    QTimer.singleShot(20, lambda: peer.write(response[2:]))

            peer.readyRead.connect(receive)
            receive()

        server.newConnection.connect(accept)
        request = OperationsTcpRequest(server.serverPort())
        outcomes = []

        def finished(status: int, payload: object) -> None:
            outcomes.append((status, payload))
            loop.quit()

        timeout = QTimer()
        timeout.setSingleShot(True)
        timeout.timeout.connect(loop.quit)
        request.finished.connect(finished)
        try:
            timeout.start(2_000)
            request.start('session-token')
            loop.exec()
        finally:
            timeout.stop()
            request.cancel()
            for sock in sockets:
                sock.abort()
            server.close()
        self.assertEqual(bytes(received), snapshot_request('session-token'))
        self.assertEqual(outcomes, [(200, snapshot)])
