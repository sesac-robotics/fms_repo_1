"""Read owner-private face-masked JPEG previews and discard stale or malformed input."""

import os
import re
import stat
from pathlib import Path
from time import time_ns

_MAX_BYTES = 2 * 1024 * 1024 + 6
_MAGIC = b'AMOV2'
_MAX_AGE_NS = 2_000_000_000


class LocalPreviewSource:
    """Read the optional, local-only field-test output from the AI Interface."""

    def __init__(self, directory: Path) -> None:
        """Retain the configured absolute directory for subsequent reads."""
        self._directory = directory

    def read(self, vehicle: str) -> tuple[bytes, int] | None:
        """Return the JPEG and masked-region count, or None when unavailable.

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
            path = directory / f'{vehicle}.preview'
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                source = os.fstat(fd)
                age = time_ns() - source.st_mtime_ns
                if (
                    source.st_uid != os.getuid()
                    or source.st_mode & 0o077
                    or not stat.S_ISREG(source.st_mode)
                    or not 11 <= source.st_size <= _MAX_BYTES
                    or not 0 <= age < _MAX_AGE_NS
                ):
                    return None
                payload = os.read(fd, _MAX_BYTES + 1)
            finally:
                os.close(fd)
        except OSError:
            return None
        jpeg = payload[6:]
        if (
            len(payload) != source.st_size
            or not payload.startswith(_MAGIC)
            or not jpeg.startswith(b'\xff\xd8\xff')
            or not jpeg.endswith(b'\xff\xd9')
        ):
            return None
        return jpeg, payload[5]
