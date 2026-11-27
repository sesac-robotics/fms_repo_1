"""Finite synthetic map and energy assumptions for the SD-09 replay."""

from collections import deque
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise


class Rejection(Enum):
    """Separate bad request, unsafe route proposal, and command failure causes."""

    INVALID = 'invalid_request'
    UNREACHABLE = 'requested_route_unreachable'
    WAYPOINT_LIMIT = 'battery_waypoint_limit'
    ENERGY = 'insufficient_route_battery'
    CONFLICT = 'request_key_conflict'


@dataclass(frozen=True)
class Plan:
    """A computed mock route; each segment is 100 m and two synthetic ticks."""

    revision: int
    locations: tuple[str, ...]
    waypoints: tuple[str, ...]
    destination: str

    @property
    def remaining_m(self) -> int:
        """Report synthetic route length in metres, from the planning origin."""
        return self.segments * 100

    @property
    def eta_ticks(self) -> int:
        """Report synthetic time ticks, independent of any wall clock."""
        return self.segments * 2

    @property
    def segments(self) -> int:
        """Return the number of traversed edges in the proposed graph path."""
        return len(self.locations) - 1


Edge = frozenset[str]


@dataclass(frozen=True)
class RoadMap:
    """An undirected fixture graph. Blocked links are excluded from planning."""

    nodes: frozenset[str]
    links: frozenset[Edge]
    blocked: frozenset[Edge] = frozenset()

    def can_traverse(self, locations: tuple[str, ...]) -> bool:
        """Check every given link against the current fixture map."""
        available = self.links - self.blocked
        return all(frozenset(edge) in available for edge in pairwise(locations))

    def path(self, start: str, stops: tuple[str, ...]) -> tuple[str, ...] | None:
        """Find a deterministic shortest open path through the ordered stop labels."""
        locations: tuple[str, ...] = (start,)
        position = start
        for target in stops:
            segment = self._shortest(position, target)
            if segment is None:
                return None
            locations += segment[1:]
            position = target
        return locations

    def _shortest(self, start: str, target: str) -> tuple[str, ...] | None:
        if start not in self.nodes or target not in self.nodes:
            return None
        queue: deque[tuple[str, ...]] = deque([(start,)])
        seen = {start}
        while queue:
            path = queue.popleft()
            if path[-1] == target:
                return path
            for node in sorted(self.nodes - seen):
                if self.can_traverse((path[-1], node)):
                    seen.add(node)
                    queue.append((*path, node))
        return None

    def plan(
        self,
        start: str,
        waypoints: tuple[str, ...],
        destination: str,
        battery_pct: int,
        revision: int,
    ) -> Plan | Rejection:
        """Require distinct known stops, a provisional waypoint cap, and energy."""
        stops = (*waypoints, destination)
        if not (
            0 <= battery_pct <= 100 and len(set((start, *stops))) == len(stops) + 1
        ):
            return Rejection.INVALID
        if not {start, *stops} <= self.nodes:
            return Rejection.INVALID
        reserve_pct = 10
        if len(waypoints) > max(0, (battery_pct - reserve_pct) // 10):
            return Rejection.WAYPOINT_LIMIT
        locations = self.path(start, stops)
        if locations is None:
            return Rejection.UNREACHABLE
        plan = Plan(revision, locations, waypoints, destination)
        if battery_pct < plan.segments * 4 + reserve_pct:
            return Rejection.ENERGY
        return plan
