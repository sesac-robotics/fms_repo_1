"""Supply a private credential only to an OpenSSH password prompt."""

import os
import stat
import sys
from pathlib import Path


def private_bytes(path: Path, limit: int) -> bytes:
    """Read a bounded owner-private regular file without following symlinks."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or not 0 < info.st_size <= limit
        ):
            raise ValueError('Expected an owner-private file.')
        data = os.read(fd, limit + 1)
        if len(data) != info.st_size:
            raise ValueError('Private file changed during read.')
        return data
    finally:
        os.close(fd)


def main() -> int:
    """Respond on the askpass pipe without logging credentials or prompts."""
    if (
        len(sys.argv) != 2
        or not sys.argv[1].rstrip().lower().endswith('password:')
        or os.environ.get('SSH_ASKPASS_PROMPT')
    ):
        return 1
    try:
        path = Path(os.environ['AMO_FMS_CAMERA_PASSWORD_FILE'])
        password = private_bytes(path, 512).removesuffix(b'\n')
        if not password or any(c in password for c in (b'\r', b'\n', b'\x00')):
            return 1
    except (KeyError, OSError, ValueError):
        return 1
    sys.stdout.buffer.write(password + b'\n')
    return 0
