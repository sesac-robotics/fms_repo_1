"""Latest-frame scheduling rules driven by caller-supplied monotonic time."""

from dataclasses import dataclass
from typing import Literal

from amo_ai_interface.frame import Frame

DropReason = Literal['frame_out_of_order', 'frame_superseded', 'frame_expired']
QUEUE_SECONDS = 0.2
CAMERA_IDLE_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class DroppedFrame:
    """A frame and the reason it was omitted from HTTP delivery."""

    frame: Frame
    reason: DropReason


class LatestFrames:
    """Keep one pending frame per allowed robot, in robot arrival order.

    The caller serializes access and supplies elapsed time in monotonic seconds.
    Pending frames expire after 200 ms. A camera may restart its stamp sequence
    after five seconds without an accepted frame.
    """

    def __init__(self, robot_ids: frozenset[str]) -> None:
        self._robot_ids = robot_ids
        self._waiting: dict[str, tuple[Frame, float]] = {}
        self._last_seen: dict[str, tuple[int, float]] = {}

    def offer(self, frame: Frame, now: float) -> DroppedFrame | None:
        """Queue a frame, returning a superseded or out-of-order frame if any.

        Raise ValueError for input from a robot outside the configured set.
        """
        robot = frame.robot_id
        if robot not in self._robot_ids:
            raise ValueError('Unknown camera robot')
        last_stamp, seen_at = self._last_seen.get(robot, (0, now))
        if frame.stamp_ns <= last_stamp and now - seen_at < CAMERA_IDLE_SECONDS:
            return DroppedFrame(frame, 'frame_out_of_order')

        previous = self._waiting.get(robot)
        self._last_seen[robot] = frame.stamp_ns, now
        self._waiting[robot] = frame, now
        if previous is None:
            return None
        old_frame, queued_at = previous
        reason = (
            'frame_expired' if now >= queued_at + QUEUE_SECONDS else 'frame_superseded'
        )
        return DroppedFrame(old_frame, reason)

    def take(self, now: float) -> tuple[Frame | None, list[DroppedFrame]]:
        """Discard expired pending frames and return the earliest waiting robot."""
        expired = []
        for robot, (frame, queued_at) in tuple(self._waiting.items()):
            if now >= queued_at + QUEUE_SECONDS:
                del self._waiting[robot]
                expired.append(DroppedFrame(frame, 'frame_expired'))
        if not self._waiting:
            return None, expired
        frame, _ = self._waiting.pop(next(iter(self._waiting)))
        return frame, expired
