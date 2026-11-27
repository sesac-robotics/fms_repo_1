"""Values and limits for frames entering the Vision delivery path."""

import re
from dataclasses import dataclass
from hashlib import blake2s

MAX_JPEG_BYTES = 2 * 1024 * 1024
NS_PER_SECOND = 1_000_000_000
_ROBOT_ID = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,31}')


def validate_robot_id(robot_id: str) -> str:
    """Return a 1–32 character ROS topic component or raise ValueError."""
    if _ROBOT_ID.fullmatch(robot_id) is None:
        raise ValueError(
            'Robot ID must contain 1–32 characters valid in a ROS subtopic'
        )
    return robot_id


def is_jpeg(image: bytes) -> bool:
    """Check the compressed JPEG transfer envelope without decoding its pixels."""
    return (
        5 <= len(image) <= MAX_JPEG_BYTES
        and image.startswith(b'\xff\xd8\xff')
        and image.endswith(b'\xff\xd9')
    )


@dataclass(frozen=True, slots=True)
class Frame:
    """A validated JPEG and the Pinky publisher's UTC acquisition stamp in ns."""

    robot_id: str
    stamp_ns: int
    jpeg: bytes

    @property
    def frame_id(self) -> str:
        """Return the delivered protocol's 32-hex-digit robot/stamp identifier."""
        robot = blake2s(self.robot_id.encode('ascii'), digest_size=8).digest()
        return (robot + self.stamp_ns.to_bytes(8, 'big')).hex()
