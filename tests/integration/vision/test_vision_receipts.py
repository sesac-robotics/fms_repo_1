"""Check receipt correlation, camera stream limits and latest-frame scheduling."""

from base64 import b64decode
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from threading import Thread
from unittest import TestCase

from amo_ai_interface.frame import Frame
from amo_ai_interface.latest_frames import LatestFrames
from amo_ai_interface.vision_http import VisionTarget, confirm_receipt
from amo_camera_streamer.camera_capture import MAX_JPEG_BYTES, jpeg_frames
from receipt_stub import receipt_server

# A generated 1×1 grayscale image exercises real JPEG bytes without camera data.
JPEG = b64decode(
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof'
    'Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAAB'
    'AAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z'
)


@contextmanager
def running_receipt(vision_id: int) -> Iterator[str]:
    """Run a diagnostic endpoint on an ephemeral IPv4 loopback port."""
    with receipt_server('127.0.0.1', 0, vision_id) as server:
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05})
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/infer'
        finally:
            server.shutdown()
            thread.join()


class CameraCaptureTest(TestCase):
    def test_camera_stream_extracts_complete_jpegs(self):
        stream = BytesIO(b'noise' + JPEG + JPEG)
        self.assertEqual(list(jpeg_frames(stream)), [JPEG, JPEG])
        self.assertFalse(stream.closed)

    def test_camera_stream_bounds_frames_and_detects_truncation(self):
        for stream in (JPEG[:-1], JPEG[:3] + bytes(MAX_JPEG_BYTES) + JPEG[-2:]):
            with self.subTest(size=len(stream)), self.assertRaises(ValueError):
                list(jpeg_frames(BytesIO(stream)))


class LatestFramesTest(TestCase):
    def setUp(self):
        self.queue = LatestFrames(frozenset({'pinky_a', 'pinky_b'}))
        self.first = Frame('pinky_a', 1, JPEG)
        self.newest = Frame('pinky_a', 2, JPEG)
        self.other = Frame('pinky_b', 1, JPEG)

    def test_one_pending_frame_per_robot_without_reordering_the_robots(self):
        self.assertIsNone(self.queue.offer(self.first, 10.0))
        self.assertIsNone(self.queue.offer(self.other, 10.01))
        dropped = self.queue.offer(self.newest, 10.02)
        self.assertIsNotNone(dropped)
        self.assertEqual(
            (dropped.frame, dropped.reason), (self.first, 'frame_superseded')
        )
        self.assertEqual(self.queue.take(10.1), (self.newest, []))
        self.assertEqual(self.queue.take(10.1), (self.other, []))

    def test_expiration_at_200ms_and_sequence_after_a_camera_restart(self):
        self.queue.offer(self.newest, 10.0)
        dropped = self.queue.offer(self.first, 10.05)
        self.assertIsNotNone(dropped)
        self.assertEqual(dropped.reason, 'frame_out_of_order')
        frame, expired = self.queue.take(10.2)
        self.assertIsNone(frame)
        self.assertEqual(
            [(d.frame, d.reason) for d in expired], [(self.newest, 'frame_expired')]
        )
        self.assertIsNone(self.queue.offer(self.first, 15.0))
        self.assertEqual(self.queue.take(15.0), (self.first, []))

    def test_unknown_camera_cannot_claim_waiting_space(self):
        with self.assertRaises(ValueError):
            self.queue.offer(Frame('unknown_camera', 1, JPEG), 0.0)


class VisionReceiptTest(TestCase):
    def test_all_three_targets_confirm_the_same_frame(self):
        frame = Frame('pinky_a', 1, JPEG)
        for vision_id in (1, 2, 3):
            with self.subTest(vision_id=vision_id), running_receipt(vision_id) as url:
                confirm_receipt(VisionTarget(vision_id, url), frame)

    def test_claiming_a_different_vision_id_fails(self):
        with running_receipt(1) as url, self.assertRaisesRegex(ValueError, 'HTTP 400'):
            confirm_receipt(VisionTarget(2, url), Frame('pinky_a', 1, JPEG))
