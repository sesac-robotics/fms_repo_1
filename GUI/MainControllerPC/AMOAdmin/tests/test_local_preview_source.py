"""Verify the local reader refuses stale and unapproved preview payloads."""

from os import utime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from unittest import TestCase

from amo_fms.local_preview_source import LocalPreviewSource


class LocalPreviewSourceTest(TestCase):
    def test_only_fresh_private_masked_jpeg_are_read_for_the_named_vehicle(
        self,
    ) -> None:
        with TemporaryDirectory() as name:
            directory = Path(name)
            reader = LocalPreviewSource(directory)
            path = directory / 'PINKY-01.preview'
            jpeg = b'\xff\xd8\xfftest\xff\xd9'
            payload = b'AMOV2\x02' + jpeg
            path.write_bytes(payload)
            path.chmod(0o600)
            self.assertEqual(reader.read('PINKY-01'), (jpeg, 2))
            self.assertIsNone(reader.read('PINKY-02'))
            utime(path, (time() - 10, time() - 10))
            self.assertIsNone(reader.read('PINKY-01'))
            path.write_bytes(b'bad preview')
            self.assertIsNone(reader.read('PINKY-01'))
