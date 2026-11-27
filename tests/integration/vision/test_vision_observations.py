"""Verify the detector JSON boundary and private observation HTTP adapter."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import time_ns
from unittest import TestCase

from amo_ai_interface.forward_observation import ForwardObservation
from amo_ai_interface.frame import Frame
from amo_ai_interface.main_control_http import MainControlWriter
from amo_ai_interface.observation import parse_detection
from amo_ai_interface.vision_http import VisionTarget, request_inference
from test_vision_receipts import JPEG, running_receipt

TEST_KEY = 'integration-test-key-for-local-fixtures-only'


@contextmanager
def fixture_http(handler: type[BaseHTTPRequestHandler]) -> Iterator[int]:
    """Bind one test handler on an ephemeral IPv4 loopback port."""
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05})
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join()


class FixtureDetector(BaseHTTPRequestHandler):
    """Emit a fixed test detection for the received input frame ID."""

    def do_POST(self) -> None:
        """Serve only the synthetic fixture's JPEG inference request."""
        if self.path != '/infer' or self.headers.get('Content-Type') != 'image/jpeg':
            self.send_error(400)
            return
        size = int(self.headers['Content-Length'])
        if self.rfile.read(size) != JPEG:
            self.send_error(400)
            return
        response = json.dumps(
            {
                'frame_id': self.headers['X-Frame-Id'],
                'outcome': 'DETECTED',
                'label': 'TEST_SIGNAL',
                'confidence': 0.75,
                'processed_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            }
        ).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args: object) -> None:
        """Keep test output focused on assertions."""


class DetectorContractTest(TestCase):
    def setUp(self) -> None:
        self.frame = Frame('test_pinky', 10_123_456_999, JPEG)
        self.response = {
            'frame_id': self.frame.frame_id,
            'outcome': 'DETECTED',
            'processed_at': '1970-01-01T00:00:11Z',
            'label': 'TEST_SIGNAL',
        }

    def test_non_detections_remain_distinct_and_omit_detection_fields(self) -> None:
        for outcome in ('NOT_DETECTED', 'UNAVAILABLE'):
            value = dict(self.response, outcome=outcome)
            del value['label']
            result = parse_detection(value, self.frame)
            self.assertEqual(
                (result.outcome, result.label, result.confidence), (outcome, None, None)
            )

    def test_rejects_mock_wrong_frame_and_invalid_results(self) -> None:
        for patch in (
            {'mock': True},
            {'frame_id': 'wrong'},
            {'label': 'invalid label'},
            {'confidence': True},
            {'confidence': 1.01},
            {'confidence': float('nan')},
            {'outcome': 'NOT_DETECTED'},
            {'processed_at': '1970-01-01T00:00:09Z'},
            {'processed_at': '1970-01-01T00:00:11+00:00'},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                parse_detection(self.response | patch, self.frame)

    def test_bad_robot_mapping_stops_before_calling_detector(self) -> None:
        action = ForwardObservation('TRAFFIC_RULES', {}, self.fail, self.fail)
        with self.assertRaisesRegex(ValueError, 'no AMO vehicle mapping'):
            action(self.frame)


class ObservationHttpTest(TestCase):
    def setUp(self) -> None:
        self.frame = Frame('test_pinky', time_ns() - 1_000_000, JPEG)

    def test_mock_receipt_never_calls_main_control_writer(self) -> None:
        with running_receipt(2) as url:
            operation = ForwardObservation(
                'TRAFFIC_RULES',
                {'test_pinky': 'PINKY-01'},
                partial(request_inference, VisionTarget(2, url)),
                self.fail,
            )
            with self.assertRaisesRegex(ValueError, 'Unexpected detector response'):
                operation(self.frame)

    def test_retry_preserves_entire_body_and_permanent_failure_is_not_retried(
        self,
    ) -> None:
        for responses in ([503, 204], [401]):
            self._exercise_responses(responses)

    def _exercise_responses(self, responses: list[int]) -> None:
        messages: list[tuple[str, str, bytes]] = []
        path = '/internal/vision/observations'

        class MainControlFixture(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                payload = self.rfile.read(int(self.headers['Content-Length']))
                messages.append((self.path, self.headers['X-AMO-Vision-Key'], payload))
                status = responses[min(len(messages) - 1, len(responses) - 1)]
                self.send_response(status)
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        with (
            fixture_http(FixtureDetector) as detector,
            fixture_http(MainControlFixture) as main,
        ):
            writer = MainControlWriter(f'http://127.0.0.1:{main}{path}', TEST_KEY)
            operation = ForwardObservation(
                'TRAFFIC_RULES',
                {'test_pinky': 'PINKY-01'},
                partial(
                    request_inference,
                    VisionTarget(2, f'http://127.0.0.1:{detector}/infer'),
                ),
                writer.send,
            )
            if responses[-1] == 204:
                operation(self.frame)
            else:
                with self.assertRaisesRegex(ValueError, 'HTTP 401'):
                    operation(self.frame)

        self.assertEqual(len(messages), len(responses))
        self.assertEqual(messages[0], messages[-1])
        requested_path, key, body = messages[0]
        self.assertEqual((requested_path, key), (path, TEST_KEY))
        data = json.loads(body)
        self.assertEqual(data['vehicleNo'], 'PINKY-01')
        self.assertEqual(data['frameId'], self.frame.frame_id)
        self.assertEqual(data['label'], 'TEST_SIGNAL')
        self.assertEqual(data['source'], 'TRAFFIC_RULES')
        self.assertEqual(data['confidence'], 0.75)
        self.assertIn('resultId', data)
        self.assertNotIn('jpeg', data)

    def test_main_control_writer_accepts_only_private_ipv4_loopback(self) -> None:
        for url in (
            'http://192.0.2.1:18100/internal/vision/observations',
            'http://localhost:18100/internal/vision/observations',
            'http://x@127.0.0.1:18100/internal/vision/observations',
            'http://127.0.0.1:18100/api/operations',
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                MainControlWriter(url, TEST_KEY)
