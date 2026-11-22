"""Test-only SD-11 Cargo workflow and evidence boundaries."""

from dataclasses import dataclass, field
from enum import Enum

from stage_two_vehicle import Scope


class State(Enum):
    """Test stages from pickup facility through verified return."""

    TO_CARGO_DEPOT = 'cargo_depot_travel'
    STOPPED_FOR_LOAD = 'cargo_depot_stopped'
    COUPLING_WAIT = 'coupling_wait'
    COUPLED = 'coupled'
    TRANSPORT = 'loaded_travel'
    STOPPED_FOR_HANDOFF = 'handoff_stopped'
    RETURN_TO_CARGO_DEPOT = 'cargo_depot_return'
    RELEASE_WAIT = 'uncoupling_wait'
    RELEASE_BLOCKED = 'uncoupling_blocked'
    RESTORE_WAIT = 'normal_config_wait'
    RETURN_TO_GARAGE = 'garage_return'
    RETURNED = 'garage_arrived'


class Event(Enum):
    """Explicit evidence kinds so hardware outcomes cannot stand in for motion."""

    LOAD_STOP = 'load_stop'
    LOADED = 'loaded'
    COUPLED = 'coupled'
    LOADED_MODE = 'loaded_mode_applied'
    HANDOFF_STOP = 'handoff_stop'
    HANDOFF = 'cargo_handoff'
    RELEASE_STOP = 'release_stop'
    DETACHED = 'detached'
    RELEASE_FAILED = 'release_failed'
    NORMAL_MODE = 'normal_mode_restored'
    GARAGE_ARRIVAL = 'garage_arrival'


@dataclass(frozen=True)
class CargoAssignment:
    """One origin, recipient stop, cart and designated release location."""

    scope: Scope
    job: str
    cart: str
    origin: str
    destination: str
    release_site: str
    garage: str


@dataclass(frozen=True)
class CargoEvidence:
    """One sequenced synthetic observation for a cart, place and assignment."""

    scope: Scope
    job: str
    cart: str
    site: str
    event: Event
    sequence: int


# Acknowledgements are intentionally outside this table of applied/observed events.
_TRANSITIONS = {
    (State.TO_CARGO_DEPOT, Event.LOAD_STOP): (
        State.STOPPED_FOR_LOAD,
        'origin',
        'IF-05',
    ),
    (State.STOPPED_FOR_LOAD, Event.LOADED): (State.COUPLING_WAIT, 'origin', 'IF-13'),
    (State.COUPLING_WAIT, Event.COUPLED): (State.COUPLED, 'origin', 'IF-13'),
    (State.COUPLED, Event.LOADED_MODE): (State.TRANSPORT, 'origin', 'IF-05'),
    (State.TRANSPORT, Event.HANDOFF_STOP): (
        State.STOPPED_FOR_HANDOFF,
        'destination',
        'IF-05',
    ),
    (State.STOPPED_FOR_HANDOFF, Event.HANDOFF): (
        State.RETURN_TO_CARGO_DEPOT,
        'destination',
        'mock_handoff',
    ),
    (State.RETURN_TO_CARGO_DEPOT, Event.RELEASE_STOP): (
        State.RELEASE_WAIT,
        'release_site',
        'IF-05',
    ),
    (State.RELEASE_WAIT, Event.DETACHED): (State.RESTORE_WAIT, 'release_site', 'IF-13'),
    (State.RELEASE_WAIT, Event.RELEASE_FAILED): (
        State.RELEASE_BLOCKED,
        'release_site',
        'IF-13',
    ),
    (State.RESTORE_WAIT, Event.NORMAL_MODE): (
        State.RETURN_TO_GARAGE,
        'release_site',
        'IF-05',
    ),
    (State.RETURN_TO_GARAGE, Event.GARAGE_ARRIVAL): (State.RETURNED, 'garage', 'IF-05'),
}


@dataclass
class Cargo:
    """Correlate achieved states and evaluate cart and vehicle reuse independently."""

    assignment: CargoAssignment
    state: State = field(default=State.TO_CARGO_DEPOT, init=False)
    observations: list[Event] = field(default_factory=list, init=False)
    held_for_review: bool = field(default=False, init=False)
    remaining_m: int | None = field(default=None, init=False)
    _latest: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Require a complete pickup, handoff and release fixture."""
        job = self.assignment
        if not all(
            (
                job.job,
                job.cart,
                job.origin,
                job.destination,
                job.release_site,
                job.garage,
            )
        ):
            raise ValueError('complete cargo assignment required')

    def observe(self, source: str, report: CargoEvidence) -> bool:
        """Advance only on fresh, matched evidence from the expected interface."""
        job = self.assignment
        if self.held_for_review or (report.scope, report.job, report.cart) != (
            job.scope,
            job.job,
            job.cart,
        ):
            return False
        edge = _TRANSITIONS.get((self.state, report.event))
        if edge is None:
            return False
        next_state, place, expected_source = edge
        if (
            report.site != getattr(job, place)
            or source != expected_source
            or report.sequence <= self._latest.get(source, -1)
        ):
            return False
        self._latest[source] = report.sequence
        self.state = next_state
        if report.event is Event.HANDOFF_STOP:
            self.remaining_m = 0
        self.observations.append(report.event)
        return True

    def observe_distance(self, scope: Scope, sequence: int, remaining_m: int) -> bool:
        """Project non-negative remaining metres from current IF-05 transport evidence."""
        if (
            self.state is not State.TRANSPORT
            or self.held_for_review
            or scope != self.assignment.scope
            or sequence <= self._latest.get('IF-05', -1)
            or remaining_m < 0
        ):
            return False
        self._latest['IF-05'] = sequence
        self.remaining_m = remaining_m
        return True

    def request_cancellation(self, scope: Scope) -> bool:
        """Hold unresolved before/after coupling cancellation for team review."""
        if scope != self.assignment.scope or Event.DETACHED in self.observations:
            return False
        self.held_for_review = True
        return True

    def cart_reusable(self) -> bool:
        """Release only after handoff and confirmed physical detachment."""
        return (
            Event.HANDOFF in self.observations and Event.DETACHED in self.observations
        )

    def vehicle_reusable(
        self, *, connected: bool, battery_pct: int, required_pct: int
    ) -> bool:
        """Require the separately observed normal mode, arrival and eligibility."""
        return (
            self.state is State.RETURNED
            and connected
            and 0 <= required_pct <= battery_pct <= 100
        )
