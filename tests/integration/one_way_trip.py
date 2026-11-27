"""In-memory SD-01 to SD-03 and SD-05 taxi fixture. Integer ticks are synthetic."""

from dataclasses import dataclass, field
from enum import Enum


class TripState(Enum):
    """Taxi states used by the one-way replay."""

    PICKUP = 'pickup_travel'
    BOARDING = 'boarding_wait'
    DESTINATION = 'destination_travel'
    STOPPED = 'stopped_wait'
    RETURNING = 'garage_travel'


@dataclass(frozen=True)
class Call:
    """One-way request and synthetic request tick. Key is scoped to a member."""

    member: str
    key: str
    origin: str
    destination: str
    requested_at: int


@dataclass(frozen=True)
class Receipt:
    """Stable receipt for the same call and its first controller intake tick."""

    trip_id: str
    call: Call
    accepted_at: int


@dataclass(frozen=True)
class Candidate:
    """Mock eligibility and dispatch display data; metres and synthetic ETA ticks."""

    vehicle: str
    connected: bool
    battery_pct: int
    required_pct: int
    route_open: bool
    available: bool
    eta: int
    position_m: tuple[int, int]


@dataclass(frozen=True)
class MotionReport:
    """Observed fixture event scoped to a trip, vehicle, command and link epoch."""

    trip_id: str
    assignment_id: str
    vehicle: str
    command: str
    epoch: int
    event: str


@dataclass
class Trip:
    """Advance the mock taxi only on matching post-command physical reports."""

    receipt: Receipt
    candidate: Candidate
    epoch: int
    assignment_id: str
    state: TripState = TripState.PICKUP
    boarded: bool = False
    destination_command: str | None = None
    events: list[str] = field(default_factory=list)

    def confirm_boarding(
        self, trip_id: str, assignment_id: str, vehicle: str, member: str
    ) -> bool:
        """Accept only mock confirmation for the current boarding assignment."""
        expected = (
            self.receipt.trip_id,
            self.assignment_id,
            self.candidate.vehicle,
            self.receipt.call.member,
        )
        assignment = trip_id, assignment_id, vehicle, member
        if self.state is not TripState.BOARDING or assignment != expected:
            return False
        self.boarded = True
        return True

    def request_departure(self, command: str) -> bool:
        """Authorize one destination command after matching boarding evidence."""
        if self.state is not TripState.BOARDING or not self.boarded:
            return False
        if self.destination_command is not None:
            return self.destination_command == command
        self.destination_command = command
        return True

    def observe(self, report: MotionReport) -> bool:
        """Reject mismatched, replayed or out-of-order physical events."""
        identity = (
            self.receipt.trip_id,
            self.assignment_id,
            self.candidate.vehicle,
            self.epoch,
        )
        occurrence = report.trip_id, report.assignment_id, report.vehicle, report.epoch
        if occurrence != identity:
            return False
        transitions = {
            (
                TripState.PICKUP,
                'pickup_stop',
                f'pickup:{self.receipt.trip_id}',
            ): TripState.BOARDING,
            (
                TripState.BOARDING,
                'departed',
                self.destination_command,
            ): TripState.DESTINATION,
            (
                TripState.DESTINATION,
                'destination_stop',
                self.destination_command,
            ): TripState.STOPPED,
        }
        if self.state is TripState.BOARDING and self.destination_command is None:
            return False
        new_state = transitions.get((self.state, report.event, report.command))
        if new_state is None:
            return False
        self.state = new_state
        self.events.append(report.event)
        return True

    def close_ride(self, member: str, *, alighted: bool) -> bool:
        """Require the mock alighting event before the return transition."""
        if self.state is not TripState.STOPPED or not alighted:
            return False
        if self.receipt.call.member != member:
            return False
        self.state = TripState.RETURNING
        self.events.append('alighted')
        return True
