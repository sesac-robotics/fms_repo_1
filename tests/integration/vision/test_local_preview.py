"""Check field-test face masking and the private preview output boundary."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep, time_ns
from unittest import TestCase

import cv2
import numpy as np
from amo_ai_interface.face_preview import PREVIEW_MAGIC, mask_regions
from amo_ai_interface.frame import Frame, is_jpeg
from amo_ai_interface.local_preview import configure_preview


class LocalPreviewTest(TestCase):
    def test_face_mask_preserves_pixels_outside_the_padded_region(self) -> None:
        image = np.full((480, 640, 3), (43, 120, 219), dtype=np.uint8)
        original = image.copy()
        self.assertEqual(mask_regions(image, [(100, 100, 40, 40)]), 1)
        self.assertFalse(image[86:154, 86:154].any())
        original[86:154, 86:154] = 0
        np.testing.assert_array_equal(image, original)

    def test_rejects_other_robot_and_publishes_only_a_private_color_preview(
        self,
    ) -> None:
        with TemporaryDirectory() as name:
            directory = Path(name)
            output = directory / 'PINKY-01.preview'
            color = np.full((480, 640, 3), (43, 120, 219), dtype=np.uint8)
            ok, encoded = cv2.imencode('.jpg', color)
            self.assertTrue(ok)
            jpeg = encoded.tobytes()
            with configure_preview(
                'pinky_example=PINKY-01', directory, frozenset({'pinky_example'})
            ) as preview:
                preview.offer(Frame('other', time_ns(), jpeg))
                self.assertFalse(output.exists())
                preview.offer(Frame('pinky_example', time_ns(), jpeg))
                deadline = monotonic() + 3
                while not output.exists() and monotonic() < deadline:
                    sleep(0.02)
                payload = output.read_bytes()
                self.assertEqual(payload[:6], PREVIEW_MAGIC + bytes([0]))
                self.assertTrue(is_jpeg(payload[6:]))
                decoded = cv2.imdecode(
                    np.frombuffer(payload[6:], np.uint8), cv2.IMREAD_COLOR
                )
                self.assertEqual(decoded.shape, color.shape)
                np.testing.assert_allclose(decoded[220, 310], color[220, 310], atol=3)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                preview.offer(Frame('pinky_example', time_ns(), b'bad JPEG'))
                deadline = monotonic() + 2
                while output.exists() and monotonic() < deadline:
                    sleep(0.02)
                self.assertFalse(output.exists())
            self.assertFalse(output.exists())
