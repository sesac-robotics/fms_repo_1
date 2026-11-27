"""Read owner-private coarse preview cells and discard stale or malformed input."""

import os
import re
import stat
from pathlib import Path
from time import time_ns

_PIXELS = 16 * 12
_MAX_AGE_NS = 2_000_000_000
_LEVELS = frozenset({0, 85, 170, 255})


class LocalPreviewSource:
    """Read the optional, local-only field-test output from the AI Interface."""

    def __init__(self, directory: Path) -> None:
        """Retain the configured absolute directory for subsequent reads."""
        self._directory = directory

    def read(self, vehicle: str) -> bytes | None:
        """Return the 192 coarse grayscale cells, or None when unavailable.

        Only the current user's files in a private directory are eligible.
        Never interpret an arbitrary image or a stale file as a camera feed.
        """
        if not re.fullmatch(r'PINKY-0[1-4]', vehicle):
            return None
        directory = self._directory
        try:
            root = directory.lstat()
            if (
                not directory.is_absolute()
                or not stat.S_ISDIR(root.st_mode)
                or root.st_uid != os.getuid()
                or root.st_mode & 0o077
            ):
                return None
            path = directory / f'{vehicle}.mosaic'
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                source = os.fstat(fd)
                age = time_ns() - source.st_mtime_ns
                if (
                    source.st_uid != os.getuid()
                    or source.st_mode & 0o077
                    or not stat.S_ISREG(source.st_mode)
                    or source.st_size != _PIXELS
                    or not 0 <= age < _MAX_AGE_NS
                ):
                    return None
                cells = os.read(fd, _PIXELS)
            finally:
                os.close(fd)
        except OSError:
            return None
        return cells if len(cells) == _PIXELS and set(cells) <= _LEVELS else None
