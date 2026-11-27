"""Value types for demand, signal observations and four-vehicle simulated executions."""

from dataclasses import dataclass
from enum import StrEnum

from .road_graph import Approach, Edge

TICKS_PER_SECOND = 10
VEHICLE_COUNT = 4


class Phase(StrEnum):
    """Observed signal phase; all-red does not permit any new entry."""

    NORTH = 'NORTH_GREEN'
    EAST = 'EAST_GREEN'
    RED = 'ALL_RED'


@dataclass(frozen=True)
class Signal:
    """Fixed signal plan with positive phase durations in 100 ms ticks."""

    north: int
    east: int
    all_red: int
    offset: int

    def at(self, tick: int) -> tuple[Phase, int]:
        """Return phase and ticks to the next change at a nonnegative elapsed tick."""
        phases = (
            (Phase.NORTH, self.north),
            (Phase.RED, self.all_red),
            (Phase.EAST, self.east),
            (Phase.RED, self.all_red),
        )
        elapsed = (tick + self.offset) % (self.north + self.east + 2 * self.all_red)
        for phase, duration in phases:
            if elapsed < duration:
                return phase, duration - elapsed
            elapsed -= duration
        raise AssertionError('Invalid signal duration')


class Motion(StrEnum):
    """Observed motion modes in a synthetic taxi approach."""

    IDLE = 'IDLE'
    APPROACHING = 'APPROACHING'
    WAITING = 'WAITING'
    CROSSING = 'CROSSING'
    EXITING = 'EXITING'


class WaitReason(StrEnum):
    """Cause of a waiting observation at the current tick."""

    RED = 'RED_SIGNAL'
    BLOCKED_EXIT = 'BLOCKED_EXIT'
    OCCUPIED = 'INTERSECTION_OCCUPIED'
    QUEUE = 'EARLIER_ARRIVAL'


@dataclass(frozen=True)
class Sample:
    """Synthetic vehicle snapshot with directed edge progress in [0, 1]."""

    vehicle_id: int
    approach: Approach
    motion: Motion
    edge: Edge
    progress: float
    goal_node_id: str | None
    load_state: str
    wait_reason: WaitReason | None = None
    blocked_by: int | None = None


@dataclass(frozen=True)
class Frame:
    """Four observations at the same elapsed 100 ms tick."""

    tick: int
    phase: Phase
    phase_remaining: int
    exit_closed: bool
    samples: tuple[Sample, ...]


@dataclass(frozen=True)
class Passage:
    """A single stop-line request and optional grant, actual entry and full exit ticks."""

    vehicle_id: int
    approach: Approach
    request_tick: int
    grant_tick: int | None = None
    entry_tick: int | None = None
    exit_tick: int | None = None


@dataclass(frozen=True)
class Demand:
    """A seeded synthetic trip generated at the start of an approach."""

    vehicle_id: int
    tick: int
    approach: Approach
    goal_node_id: str
    load_state: str


@dataclass(frozen=True)
class Trial:
    """One independently seeded run, with synthetic timestamps and complete observations."""

    seed: int
    duration_ticks: int
    demand_level: str
    signal: Signal
    frames: tuple[Frame, ...]
    passages: tuple[Passage, ...]
    demand: tuple[Demand, ...]
