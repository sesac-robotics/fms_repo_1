"""Read the current synthetic run carried alongside the operations snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """A committed review step and its status and reason codes."""

    step: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class Playback:
    """A single current run and its ordered simulated checkpoints."""

    run_id: UUID
    vehicle: str
    checkpoints: tuple[Checkpoint, ...]

    @classmethod
    def parse(cls, value: object) -> Playback | None:
        """Decode bounded checkpoints from the optional demo-only snapshot field."""
        if value is None:
            return None
        if not isinstance(value, dict) or not isinstance(value.get('vehicle'), str):
            raise ValueError('Invalid review playback.')
        raw_id, rows = value.get('runId'), value.get('checkpoints')
        if not isinstance(raw_id, str) or not isinstance(rows, list) or len(rows) > 64:
            raise ValueError('Invalid review checkpoint list.')
        checkpoints = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Invalid review checkpoint.')
            step, status, reason = (
                row.get(key) for key in ('step', 'status', 'reason')
            )
            if (
                not isinstance(step, str)
                or not isinstance(status, str)
                or not isinstance(reason, str)
            ):
                raise ValueError('Invalid review checkpoint codes.')
            checkpoints.append(Checkpoint(step, status, reason))
        return cls(UUID(raw_id), value['vehicle'], tuple(checkpoints))
