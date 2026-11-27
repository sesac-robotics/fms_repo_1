"""Offline SD-09 request outcomes, route revisions, and distinct re-departure."""

from dataclasses import dataclass, field
from enum import Enum

from one_way_trip import Call, TripState
from stage_two_planning import Plan, Rejection, RoadMap
from stage_two_vehicle import Evidence, Scope


class ReportKind(Enum):
    """IF-04 command receipts and application outcomes."""

    ACKNOWLEDGED = 'acknowledged'
    APPLIED = 'applied'
    FAILED = 'failed'


class RouteStatus(Enum):
    """Live-road condition, independent of any requested route change."""

    CLEAR = 'active_route_clear'
    REPLAN_REQUIRED = 'active_route_needs_replan'
    SAFE_WAIT = 'active_route_blocked_wait_safely'


@dataclass(frozen=True)
class Change:
    """Owner request with an idempotency key, vehicle scope and ordered stops."""

    key: str
    scope: Scope
    member: str
    destination: str
    waypoints: tuple[str, ...] = ()
    additional_after_stop: bool = False


@dataclass
class RouteFlow:
    """Keep the original call and effective plan until proven controller application."""

    scope: Scope
    initial_call: Call
    position: str
    state: TripState
    effective: Plan
    history: list[tuple[str, int | None]] = field(default_factory=list, init=False)
    _submissions: dict[str, tuple[Change, Plan | Rejection]] = field(
        default_factory=dict, init=False
    )
    _pending: dict[int, tuple[Plan, bool]] = field(default_factory=dict, init=False)
    _acknowledged: set[int] = field(default_factory=set, init=False)
    _revision: int = field(init=False)
    _result_sequence: int = field(default=-1, init=False)
    _motion_sequence: int = field(default=-1, init=False)
    _restart_revision: int | None = field(default=None, init=False)
    _departure: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Start the mock after the original dispatch with an existing route."""
        self._revision = self.effective.revision

    def submit(
        self, request: Change, roads: RoadMap, battery_pct: int
    ) -> Plan | Rejection:
        """Check current ownership, classify by state and plan without changing the UI."""
        if not request.key or request.scope != self.scope:
            return Rejection.INVALID
        if request.member != self.initial_call.member:
            return Rejection.INVALID
        previous = self._submissions.get(request.key)
        if previous is not None:
            return previous[1] if previous[0] == request else Rejection.CONFLICT
        needed = (
            TripState.STOPPED
            if request.additional_after_stop
            else TripState.DESTINATION
        )
        if self.state is not needed or self._departure is not None:
            return self._reject(request, Rejection.INVALID)
        proposal = roads.plan(
            self.position,
            request.waypoints,
            request.destination,
            battery_pct,
            self._revision + 1,
        )
        if isinstance(proposal, Rejection):
            return self._reject(request, proposal)
        self._revision = proposal.revision
        self._pending[proposal.revision] = proposal, request.additional_after_stop
        self._submissions[request.key] = request, proposal
        self.history.append(('planned', proposal.revision))
        return proposal

    def _reject(self, request: Change, reason: Rejection) -> Rejection:
        self._submissions[request.key] = request, reason
        self.history.append((reason.value, None))
        return reason

    def receive(
        self, kind: ReportKind, report: Evidence, reported_revision: int
    ) -> bool:
        """Correlate IF-04 evidence; only actual application updates the effective plan."""
        planned = self._pending.get(reported_revision)
        if planned is None or reported_revision <= self.effective.revision:
            return False
        if not self._matches(
            report, f'route:{reported_revision}', self._result_sequence
        ):
            return False
        match kind:
            case ReportKind.ACKNOWLEDGED if reported_revision not in self._acknowledged:
                self._acknowledged.add(reported_revision)
            case ReportKind.APPLIED:
                self.effective, stopped_addition = planned
                self._restart_revision = reported_revision if stopped_addition else None
                self._pending = {
                    revision: candidate
                    for revision, candidate in self._pending.items()
                    if revision > reported_revision
                }
                self._acknowledged.intersection_update(self._pending)
                self._departure = None
            case ReportKind.FAILED:
                del self._pending[reported_revision]
                self._acknowledged.discard(reported_revision)
            case _:
                return False
        self._result_sequence = report.sequence
        self.history.append((kind.value, reported_revision))
        return True

    def road_status(self, roads: RoadMap) -> RouteStatus:
        """Distinguish a blocked active route from a rejected request to change it."""
        if roads.can_traverse(self.effective.locations):
            return RouteStatus.CLEAR
        if roads.path(
            self.position, (*self.effective.waypoints, self.effective.destination)
        ):
            return RouteStatus.REPLAN_REQUIRED
        return RouteStatus.SAFE_WAIT

    def authorize_departure(self) -> str | None:
        """Allow a separate command after a stopped-wait destination is applied."""
        if (
            self.state is not TripState.STOPPED
            or self._restart_revision != self.effective.revision
            or self._pending
        ):
            return None
        self._departure = f'depart:{self.effective.revision}'
        return self._departure

    def observe_departure(self, report: Evidence) -> bool:
        """Change state only for matched IF-05 actual departure after authorization."""
        if self.state is not TripState.STOPPED or self._departure is None:
            return False
        if not self._matches(report, self._departure, self._motion_sequence):
            return False
        self._motion_sequence = report.sequence
        self.state = TripState.DESTINATION
        self._departure = None
        self._restart_revision = None
        self.history.append(('departed', self.effective.revision))
        return True

    def _matches(self, report: Evidence, command: str, previous: int) -> bool:
        return (
            report.scope == self.scope
            and report.command == command
            and report.sequence > previous
        )
