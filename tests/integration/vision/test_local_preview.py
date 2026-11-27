"""Exercise the exact field-test preview encoder without a physical camera."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep, time_ns
from unittest import TestCase

from amo_ai_interface.frame import Frame
from amo_ai_interface.local_preview import configure_preview
from test_vision_receipts import JPEG


class LocalPreviewTest(TestCase):
    def test_only_coarse_cells_from_the_mapped_robot_reach_the_display_file(
        self,
    ) -> None:
        with TemporaryDirectory() as name:
            directory = Path(name)
            output = directory / 'PINKY-01.mosaic'
            with configure_preview(
                'pinky_example=PINKY-01', directory, frozenset({'pinky_example'})
            ) as preview:
                preview.offer(Frame('other', time_ns(), JPEG))
                self.assertFalse(output.exists())
                preview.offer(Frame('pinky_example', time_ns(), JPEG))
                deadline = monotonic() + 2
                while not output.exists() and monotonic() < deadline:
                    sleep(0.02)
                cells = output.read_bytes()
                self.assertEqual(len(cells), 192)
                self.assertLessEqual(set(cells), {0, 85, 170, 255})
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertFalse(output.exists())
