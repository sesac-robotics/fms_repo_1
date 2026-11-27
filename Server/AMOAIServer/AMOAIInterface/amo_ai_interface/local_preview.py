"""Produce a coarse, whole-frame mosaic for the local FMS field test."""

import logging
import re
from collections import deque
from collections.abc import Callable
from os import getuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Condition, Thread

from amo_ai_interface.frame import Frame, validate_robot_id

_WIDTH, _HEIGHT = 16, 12
_LEVELS = frozenset({0, 85, 170, 255})


def configure_preview(
    mapping: str, directory: Path, robot_ids: frozenset[str]
) -> 'LocalPreview':
    """Bind one allowed ROS robot to one fleet slot in an owner-private directory."""
    robot, _, vehicle = mapping.partition('=')
    if validate_robot_id(robot) not in robot_ids or not re.fullmatch(
        r'PINKY-0[1-4]', vehicle
    ):
        raise ValueError('Local preview requires a configured ROBOT=PINKY-0N')
    if (
        not directory.is_absolute()
        or not directory.is_dir()
        or directory.is_symlink()
        or directory.stat().st_mode & 0o077
        or directory.stat().st_uid != getuid()
    ):
        raise ValueError('Local preview requires an existing owner-private directory')
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError('Local preview requires OpenCV and NumPy') from exc

    def mosaic(jpeg: bytes) -> bytes:
        image = cv2.imdecode(
            np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_REDUCED_GRAYSCALE_8
        )
        if image is None or not image.size:
            raise ValueError('Could not decode the camera JPEG')
        cells = cv2.resize(image, (_WIDTH, _HEIGHT), interpolation=cv2.INTER_AREA)
        return ((cells // 64) * 85).tobytes()

    return LocalPreview(robot, directory / f'{vehicle}.mosaic', mosaic)


class LocalPreview:
    """Own one worker and one pending frame, publishing only coarse grayscale cells."""

    def __init__(
        self, robot_id: str, output: Path, mask: Callable[[bytes], bytes]
    ) -> None:
        self._robot_id = robot_id
        self._output = output
        self._mask = mask
        self._pending: deque[Frame] = deque(maxlen=1)
        self._ready = Condition()
        self._closed = False
        self._worker = Thread(target=self._run, name='local-camera-preview')

    def __enter__(self) -> 'LocalPreview':
        """Remove a stale preview and start the worker."""
        self._output.unlink(missing_ok=True)
        self._worker.start()
        return self

    def __exit__(self, *_error: object) -> None:
        """Release the worker and remove the most recent display file."""
        with self._ready:
            self._closed = True
            self._pending.clear()
            self._ready.notify()
        self._worker.join()
        self._output.unlink(missing_ok=True)

    def offer(self, frame: Frame) -> None:
        """Offer a validated frame without blocking on masking or file writes."""
        if frame.robot_id != self._robot_id:
            return
        with self._ready:
            self._pending.append(frame)
            self._ready.notify()

    def _run(self) -> None:
        while True:
            with self._ready:
                self._ready.wait_for(lambda: self._pending or self._closed)
                if self._closed:
                    return
                frame = self._pending.pop()
            try:
                cells = self._mask(frame.jpeg)
                if len(cells) != _WIDTH * _HEIGHT or not set(cells) <= _LEVELS:
                    raise ValueError('Unexpected mosaic dimensions or palette')
                self._publish(cells)
                logging.info(
                    'local_preview_written frame=%s vehicle=%s',
                    frame.frame_id,
                    self._output.stem,
                )
            except Exception as error:
                # Camera decode failures must never fall back to the original JPEG.
                self._output.unlink(missing_ok=True)
                logging.warning(
                    'local_preview_withheld error_type=%s', type(error).__name__
                )

    def _publish(self, cells: bytes) -> None:
        with NamedTemporaryFile(dir=self._output.parent, delete=False) as scratch:
            temporary = Path(scratch.name)
            try:
                scratch.write(cells)
                scratch.close()
                temporary.replace(self._output)
            finally:
                temporary.unlink(missing_ok=True)
