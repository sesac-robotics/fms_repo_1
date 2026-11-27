"""Test-only SD-10 Hold state machine using caller-supplied integer ticks."""

from dataclasses import dataclass, field
from enum import Enum

from one_way_depot import Billing, Payment, Purpose, Slot
from stage_two_vehicle import Scope


class State(Enum):
    """Operational checkpoints projected by the Hold fixture."""

    READY = 'ready'
    MOVING = 'destination_travel'
    STOPPED = 'stopped_wait'
    PARKING = 'automatic_parking'
    PARKED = 'parking_wait'
    RETURN_WAIT = 'return_wait'
    RETURNING = 'garage_travel'
    RETURNED = 'garage_arrived'


@dataclass(frozen=True)
class HoldRequest:
    """SD-10 initial pickup and positive duration in synthetic seconds."""

    owner: str
    pickup: str
    duration: int
    destination: str | None = None


@dataclass
class Rental:
    """Replay motion, parking and closeout using one assignment and no wall clock."""

    call: HoldRequest
    scope: Scope
    state: State = field(default=State.READY, init=False)
    destination: str | None = field(default=None, init=False)
    started_at: int | None = field(default=None, init=False)
    ended_at: int | None = field(default=None, init=False)
    return_reason: str | None = field(default=None, init=False)
    return_origin: State | None = field(default=None, init=False)
    slot: Slot | None = field(default=None, init=False)
    _command: str | None = field(default=None, init=False)
    _clock: int = field(default=-1, init=False)
    _stopped: bool = field(default=False, init=False)
    _alighted: bool = field(default=False, init=False)
    _billing: Billing = field(default_factory=Billing, init=False)

    def __post_init__(self) -> None:
        """Apply the SR-002 initial call shape for this mock."""
        if not self.call.owner or not self.call.pickup or self.call.duration <= 0:
            raise ValueError('owner, pickup and positive duration required')
        if self.call.destination is not None:
            raise ValueError('first Hold call uses pickup and duration only')

    def remaining(self, tick: int) -> int | None:
        """Return remaining synthetic seconds, or None before handover confirmation."""
        if self.started_at is None:
            return None
        used_until = min(tick, self.ended_at) if self.ended_at is not None else tick
        return max(0, self.call.duration - max(0, used_until - self.started_at))

    def confirm_handover(self, scope: Scope, owner: str, tick: int) -> bool:
        """Start timing once on matching handover evidence in synthetic seconds."""
        if (scope, owner) != (self.scope, self.call.owner):
            return False
        if self.started_at is not None or tick < 0:
            return False
        self.started_at = self._clock = tick
        return True

    def set_destination(self, owner: str, target: str, command: str) -> bool:
        """Bind a later route command. Command intake never proves departure."""
        if owner != self.call.owner or not target or not command or self.return_reason:
            return False
        if self.state not in {State.READY, State.MOVING, State.STOPPED, State.PARKED}:
            return False
        self.destination, self._command = target, command
        return True

    def assign_bay(self, bay: str, *, free: bool) -> bool:
        """Start automatic parking after the stop, using an available bay."""
        if self.state is not State.STOPPED or self.return_reason or not free or not bay:
            return False
        self.slot = Slot(bay, self.scope.vehicle, Purpose.PARK)
        self.state = State.PARKING
        return True

    def parking_event(self, scope: Scope, bay: str, event: str) -> bool:
        """Apply the matching Dev-shaped occupancy/exit or vehicle bay arrival."""
        if scope != self.scope or self.slot is None:
            return False
        if self.state not in {State.PARKING, State.PARKED, State.RETURN_WAIT}:
            return False
        if not self.slot.observe(bay, scope.vehicle, event):
            return False
        if event == 'occupied' and self.state is State.PARKING:
            self.state = State.PARKED
        self._ready_to_return()
        return True

    def request_return(self, owner: str, tick: int) -> bool:
        """Start a direct return from a verified stationary or parked phase."""
        if owner != self.call.owner or tick < self._clock:
            return False
        return self._start_return('manual', tick)

    def expire(self, tick: int) -> bool:
        """Enter return wait on an inclusive, supplied deadline."""
        if tick < self._clock or self.remaining(tick) != 0:
            return False
        return self._start_return('expired', tick)

    def _start_return(self, reason: str, tick: int) -> bool:
        if self.started_at is None or self.return_reason:
            return False
        if self.state not in {State.READY, State.MOVING, State.STOPPED, State.PARKED}:
            return False
        if self.state is State.MOVING and reason != 'expired':
            return False
        self.return_origin = self.state
        self.return_reason = reason
        self._stopped = self.state is not State.MOVING
        self.ended_at = min(tick, self.started_at + self.call.duration)
        self._clock = tick
        if self.state is State.MOVING:
            self.state = State.RETURN_WAIT
        self._command = 'return'
        return True

    def vehicle_event(self, scope: Scope, command: str, event: str, tick: int) -> bool:
        """Correlate synthetic IF-05 evidence with the current command and clock."""
        if scope != self.scope or command != self._command or tick < self._clock:
            return False
        match event, self.state:
            case 'departed', State.READY | State.STOPPED | State.PARKED if (
                not self.return_reason
            ):
                if self.slot is not None and not self.slot.exited:
                    return False
                if self.started_at is None or self.remaining(tick) == 0:
                    return False
                self.state = State.MOVING
                self.slot = None
            case 'destination_stop', State.MOVING:
                self.state = State.STOPPED
            case 'safely_stopped', State.RETURN_WAIT if not self._stopped:
                self._stopped = True
            case 'garage_arrived', State.RETURNING:
                self.state = State.RETURNED
            case _:
                return False
        self._clock = tick
        return True

    def confirm_alighting(self, scope: Scope, owner: str, tick: int) -> bool:
        """Accept an adjudicated alighting only once the return is safely stopped."""
        if not (
            scope == self.scope and owner == self.call.owner and tick >= self._clock
        ):
            return False
        if not self.return_reason or not self._stopped or self._alighted:
            return False
        self._alighted, self._clock = True, tick
        self._ready_to_return()
        return True

    def _ready_to_return(self) -> None:
        if self.return_reason and self._alighted:
            if self.slot is None or self.slot.exited:
                self.state = State.RETURNING

    def settle(
        self, key: str, *, distance_m: int, method: bool, succeeds: bool
    ) -> Payment | None:
        """Project a mock billing outcome independently of reuse eligibility."""
        if self.state is not State.RETURNED:
            return None
        assert self.started_at is not None and self.ended_at is not None
        return self._billing.settle(
            self.scope.trip,
            key,
            distance_m=distance_m,
            duration_ticks=self.ended_at - self.started_at,
            method_registered=method,
            payment_succeeds=succeeds,
        )

    def reusable(self, *, connected: bool, battery_pct: int, required_pct: int) -> bool:
        """Evaluate a later allocation independently of the mock fee."""
        return (
            self.state is State.RETURNED
            and connected
            and 0 <= required_pct <= battery_pct <= 100
        )
