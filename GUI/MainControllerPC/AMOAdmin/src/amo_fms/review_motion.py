"""Interpolate display-only motion between committed synthetic map checkpoints."""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]
DURATION_SECONDS = 1.25


@dataclass(frozen=True, slots=True)
class ReviewMotion:
    """A bounded visual transition in v0.2 map meters, on a monotonic clock."""

    start: Point
    end: Point
    started: float

    def position(self, now: float) -> Point:
        """Return the displayed point at monotonic seconds now."""
        fraction = min(1.0, max(0.0, (now - self.started) / DURATION_SECONDS))
        if fraction == 1.0:
            return self.end
        x1, y1 = self.start
        x2, y2 = self.end
        return x1 + (x2 - x1) * fraction, y1 + (y2 - y1) * fraction
