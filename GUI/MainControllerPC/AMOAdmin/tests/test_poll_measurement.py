"""Verify that a delayed IF-03 failure records a skipped poll separately."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
from PyQt6.QtNetwork import QHostAddress, QTcpServer

from amo_fms.api import PreviewApi


class PollMeasurementTests(unittest.TestCase):
    """Exercise a delayed failure against an isolated loopback test endpoint."""

    def test_in_flight_skip_and_failed_response_are_independent(self) -> None:
        app = QCoreApplication.instance() or QCoreApplication([])
        self.assertIsNotNone(app)
        server = QTcpServer()
        self.assertTrue(server.listen(QHostAddress('127.0.0.1'), 0))
        payload = json.dumps({'status': 503, 'headers': {}, 'body': ''}).encode()
        frame = len(payload).to_bytes(4, 'big') + payload
        loop = QEventLoop()

        def accept() -> None:
            peer = server.nextPendingConnection()
            QTimer.singleShot(30, lambda: peer.write(frame))

        server.newConnection.connect(accept)
        api = PreviewApi('http://127.0.0.1:18085', server.serverPort())
        api._token = 'synthetic-test-session'
        error = []
        api.failed.connect(
            lambda kind, detail: (error.append((kind, detail)), loop.quit())
        )
        deadline = QTimer()
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        with TemporaryDirectory() as directory:
            trace = Path(directory) / 'poll.jsonl'
            with patch.dict('os.environ', AMO_FMS_TRACE=str(trace)):
                deadline.start(2000)
                api.refresh()
                api.refresh()
                loop.exec()
                deadline.stop()
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
        server.close()
        self.assertEqual(
            [row['event'] for row in rows],
            [
                'poll_started',
                'poll_skipped',
                'poll_response',
            ],
        )
        self.assertEqual(rows[-1]['status'], 503)
        self.assertEqual(error, [('operations', 'snapshot_unavailable')])
