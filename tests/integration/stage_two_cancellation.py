"""Offline SD-08 cancellation, cleanup, and return events."""

from dataclasses import dataclass, field
from enum import Enum

from stage_two_vehicle import Evidence, Scope


class Phase(Enum):
    """Cancellation checkpoints observable in the fixture."""

    QUEUED = 'queued'
    PICKUP = 'pickup'
    BOARDING = 'boarding'
    BOARDED = 'boarded'
    CLEANUP = 'cleanup_required'
    CANCELLED = 'cancelled_unassigned'
    RETURNING = 'returning'
    RETURNED = 'returned'


class Cause(Enum):
    """Passenger request and scheduler event remain separate audit causes."""

    USER = 'user_cancel'
    NO_SHOW = 'no_show_timeout'


class ReportKind(Enum):
    """Fixture event kinds, where command acceptance carries no motion evidence."""

    PICKUP_STOP = 'pickup_stop'
    ACKNOWLEDGED = 'acknowledged'
    FAILED = 'cleanup_failed'
    ACTUAL_STOP = 'actual_stop'
    OLD_WORK_RELEASED = 'old_work_released'
    RETURN_ARRIVAL = 'return_arrival'


@dataclass(frozen=True)
class Cancellation:
    """A trip-scoped operation key and the exact cause and source identity."""

    trip: str
    key: str
    cause: Cause
    member: str | None
    timer_scope: Scope | None = None


@dataclass
class CancelFlow:
    """Model intake, safe vehicle cleanup and availability as separate facts."""

    trip: str
    owner: str
    scope: Scope | None
    phase: Phase
    history: list[str] = field(default_factory=list, init=False)
    cancellation: Cancellation | None = field(default=None, init=False)
    assignment_open: bool = field(default=False, init=False)
    cleanup_acknowledged: bool = field(default=False, init=False)
    stopped: bool = field(default=False, init=False)
    released: bool = field(default=False, init=False)
    cleanup_failed: bool = field(default=False, init=False)
    _result_sequence: int = field(default=-1, init=False)
    _motion_sequence: int = field(default=-1, init=False)

    def __post_init__(self) -> None:
        """Only an assigned fixture starts in the pickup phase."""
        if self.phase not in {Phase.QUEUED, Phase.PICKUP}:
            raise ValueError('start from queued or pickup')
        if self.scope is None and self.phase is Phase.QUEUED:
            return
        if (
            self.scope is None
            or self.scope.trip != self.trip
            or self.phase is Phase.QUEUED
        ):
            raise ValueError('phase requires matching assignment')
        self.assignment_open = True

    def submit(self, request: Cancellation) -> Phase | None:
        """Validate a request and return its current status; namespace keys by trip."""
        if request.trip != self.trip or not request.key:
            return None
        if request == self.cancellation:
            return self.phase
        if self.cancellation is not None:
            return None
        if request.cause is Cause.USER:
            allowed = {Phase.QUEUED, Phase.PICKUP, Phase.BOARDING}
            valid = (
                request.member == self.owner
                and request.timer_scope is None
                and self.phase in allowed
            )
        else:
            valid = (
                request.member is None
                and self.phase is Phase.BOARDING
                and request.timer_scope == self.scope
            )
        if not valid:
            return None
        self.cancellation = request
        self.history.append(request.cause.value)
        self.phase = Phase.CLEANUP if self.assignment_open else Phase.CANCELLED
        return self.phase

    def confirm_boarding(self, scope: Scope, member: str) -> bool:
        """Process boarding in arrival order with cancellation and timeout events."""
        if (
            self.phase is not Phase.BOARDING
            or scope != self.scope
            or member != self.owner
        ):
            return False
        self.phase = Phase.BOARDED
        self.history.append('boarding_confirmed')
        return True

    def observe(self, kind: ReportKind, report: Evidence) -> bool:
        """Apply only matched, fresh reports for the current synthetic operation."""
        result_report = kind in {ReportKind.ACKNOWLEDGED, ReportKind.FAILED}
        previous = self._result_sequence if result_report else self._motion_sequence
        if report.scope != self.scope or report.sequence <= previous:
            return False
        if not self._apply(kind, report.command):
            return False
        if result_report:
            self._result_sequence = report.sequence
        else:
            self._motion_sequence = report.sequence
        self.history.append(kind.value)
        if self.phase is Phase.CLEANUP and self.stopped and self.released:
            self.assignment_open = False
            self.phase = Phase.RETURNING
            self.history.append('assignment_closed')
        return True

    def _apply(self, kind: ReportKind, command: str) -> bool:
        if self.phase is Phase.PICKUP and kind is ReportKind.PICKUP_STOP:
            if command != f'pickup:{self.trip}':
                return False
            self.phase = Phase.BOARDING
            return True
        if self.cancellation is None:
            return False
        key = self.cancellation.key
        if self.phase is Phase.RETURNING and kind is ReportKind.RETURN_ARRIVAL:
            if command != f'return:{key}':
                return False
            self.phase = Phase.RETURNED
            return True
        if (
            self.phase is not Phase.CLEANUP
            or self.cleanup_failed
            or command != f'cleanup:{key}'
        ):
            return False
        match kind:
            case ReportKind.ACKNOWLEDGED if not self.cleanup_acknowledged:
                self.cleanup_acknowledged = True
            case ReportKind.FAILED:
                self.cleanup_failed = True
            case ReportKind.ACTUAL_STOP if not self.stopped:
                self.stopped = True
            case ReportKind.OLD_WORK_RELEASED if not self.released:
                self.released = True
            case _:
                return False
        return True

    def can_dispatch(
        self, *, connected: bool, healthy: bool, battery_pct: int, required_pct: int
    ) -> bool:
        """Require separate return and current link/health/percent eligibility evidence."""
        return (
            self.phase is Phase.RETURNED
            and connected
            and healthy
            and 0 <= required_pct <= battery_pct <= 100
        )
