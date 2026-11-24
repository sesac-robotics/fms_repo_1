"""Test-only SD-11 Cargo workflow and evidence boundaries."""

from dataclasses import dataclass, field

from cargo_transitions import TRANSITIONS
from cargo_transitions import Event as Event
from cargo_transitions import State as State
from stage_two_vehicle import Scope


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
    pickup: str


@dataclass(frozen=True)
class CargoEvidence:
    """One sequenced synthetic observation for a cart, place and assignment."""

    scope: Scope
    job: str
    cart: str
    site: str
    event: Event
    sequence: int


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
                job.pickup,
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
        edge = TRANSITIONS.get((self.state, report.event))
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
