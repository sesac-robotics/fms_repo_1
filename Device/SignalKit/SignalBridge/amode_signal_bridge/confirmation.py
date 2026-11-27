"""Track whether the signal has confirmed the commands the bridge published.

The firmware reports the last command it handled as ``lastCommand``. Commands
are handled in order, so seeing the newest published command confirms the
whole outstanding batch. Every command is idempotent (AUTO, HOLD, PLAN), so an
unconfirmed batch can be published again without changing the outcome.
Times are monotonic seconds supplied by the caller; this module does no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """What the caller should do with the outstanding commands."""

    WAIT = 'wait'
    RESEND = 'resend'
    GIVE_UP = 'give_up'


@dataclass(frozen=True)
class Decision:
    """An action and the commands it applies to, oldest first."""

    action: Action
    commands: tuple[str, ...] = ()


class CommandConfirmation:
    """Outstanding-command state with a bounded number of resends.

    Not thread-safe: the owner serializes calls.
    """

    def __init__(self, timeout_s: float = 2.0, max_attempts: int = 3) -> None:
        """Wait ``timeout_s`` between attempts and stop after ``max_attempts``."""
        if timeout_s <= 0 or max_attempts < 1:
            raise ValueError('timeout_s must be positive and max_attempts >= 1')
        self._timeout_s = timeout_s
        self._max_attempts = max_attempts
        self._pending: list[str] = []
        self._sent_at = 0.0
        self._attempts = 0

    @property
    def pending(self) -> tuple[str, ...]:
        """Commands published but not yet confirmed, oldest first."""
        return tuple(self._pending)

    def sent(self, command: str, now_s: float) -> None:
        """Record a newly published command; restarts the attempt count."""
        self._pending.append(command)
        self._sent_at = now_s
        self._attempts = 1

    def observe(self, last_command: object) -> None:
        """Clear the batch when the signal reports its newest command."""
        if self._pending and last_command == self._pending[-1]:
            self._pending.clear()

    def poll(self, now_s: float) -> Decision:
        """Decide whether to wait, resend the batch, or give up on it."""
        if not self._pending or now_s - self._sent_at < self._timeout_s:
            return Decision(Action.WAIT)
        batch = tuple(self._pending)
        if self._attempts >= self._max_attempts:
            self._pending.clear()
            return Decision(Action.GIVE_UP, batch)
        self._attempts += 1
        self._sent_at = now_s
        return Decision(Action.RESEND, batch)
