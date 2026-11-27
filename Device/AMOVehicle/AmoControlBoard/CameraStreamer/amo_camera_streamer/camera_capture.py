"""Read bounded JPEG frames from the Pinky front camera."""

from collections.abc import Iterator
from contextlib import contextmanager
from subprocess import PIPE, Popen, TimeoutExpired
from typing import BinaryIO

MAX_JPEG_BYTES = 2 * 1024 * 1024
_START = b'\xff\xd8\xff'
_END = b'\xff\xd9'


def jpeg_frames(stream: BinaryIO) -> Iterator[bytes]:
    """Yield complete MJPEG frames of at most 2 MiB from a caller-owned stream.

    Raise ValueError for an oversized or truncated frame. Ignore bytes before
    the first JPEG marker.
    """
    buffer = bytearray()
    search_from = len(_START)
    while chunk := stream.read1(65_536):
        buffer.extend(chunk)
        while buffer:
            start = buffer.find(_START)
            if start < 0:
                del buffer[: -(len(_START) - 1)]
                break
            del buffer[:start]
            end = buffer.find(_END, search_from)
            if end < 0:
                if len(buffer) >= MAX_JPEG_BYTES:
                    raise ValueError('Camera JPEG exceeds 2 MiB')
                search_from = max(len(_START), len(buffer) - 1)
                break
            length = end + len(_END)
            if length > MAX_JPEG_BYTES:
                raise ValueError('Camera JPEG exceeds 2 MiB')
            yield bytes(buffer[:length])
            del buffer[:length]
            search_from = len(_START)
    if buffer.startswith(_START):
        raise ValueError('Camera stopped inside a JPEG')


@contextmanager
def open_camera() -> Iterator[BinaryIO]:
    """Own an rpicam-vid child and its 640×480, 5 FPS, 180° MJPEG stream.

    Propagate startup errors from the operating system. On exit terminate the
    child and allow it three seconds before killing it.
    """
    camera = Popen(
        [
            'rpicam-vid',
            '--nopreview',
            '--timeout',
            '0',
            '--width',
            '640',
            '--height',
            '480',
            '--rotation',
            '180',
            '--framerate',
            '5',
            '--codec',
            'mjpeg',
            '--flush',
            '--output',
            '-',
        ],
        stdout=PIPE,
    )
    try:
        assert camera.stdout is not None
        yield camera.stdout
    finally:
        if camera.poll() is None:
            camera.terminate()
        try:
            camera.wait(timeout=3)
        except TimeoutExpired:
            camera.kill()
            camera.wait()
        finally:
            if camera.stdout is not None:
                camera.stdout.close()
