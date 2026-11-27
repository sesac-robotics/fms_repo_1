"""Run a deterministic four-taxi traffic simulation without external resources."""

from dataclasses import dataclass, replace
from math import ceil
from random import Random

from .road_graph import LANES, Approach, Edge
from .trial import (
    TICKS_PER_SECOND,
    VEHICLE_COUNT,
    Demand,
    Frame,
    Motion,
    Passage,
    Phase,
    Sample,
    Signal,
    Trial,
    WaitReason,
)

DEMAND_LEVELS = ('LIGHT', 'MEDIUM', 'HEAVY')
_PAUSES = ((55, 290), (30, 160), (5, 60))


@dataclass
class _Car:
    id: int
    motion: Motion = Motion.IDLE
    approach: Approach = Approach.NORTH
    start: int = 0
    until: int = 0
    load: str = 'EMPTY'
    passage: int = -1

    def begin(self, motion: Motion, tick: int, duration: int) -> None:
        self.motion, self.start, self.until = motion, tick, tick + duration


def _travel(edge: Edge) -> int:
    return ceil(TICKS_PER_SECOND * edge.length_m / edge.speed_limit_mps)


def _eligible(car: _Car, phase: Phase) -> bool:
    return phase.value == f'{car.approach.value}_GREEN'


def _advance(
    car: _Car,
    tick: int,
    rng: Random,
    passages: list[Passage],
    demand: list[Demand],
    level: int,
) -> None:
    if tick < car.until:
        return
    match car.motion:
        case Motion.IDLE:
            car.approach = rng.choice(tuple(Approach))
            car.load = rng.choice(('EMPTY', 'PASSENGER'))
            approach, _, exit_edge = LANES[car.approach]
            demand.append(
                Demand(car.id, tick, car.approach, exit_edge.target.id, car.load)
            )
            car.begin(Motion.APPROACHING, tick, _travel(approach) + rng.randrange(21))
        case Motion.APPROACHING:
            car.passage = len(passages)
            passages.append(Passage(car.id, car.approach, tick))
            car.begin(Motion.WAITING, tick, 0)
        case Motion.CROSSING:
            passages[car.passage] = replace(passages[car.passage], exit_tick=tick)
            car.begin(Motion.EXITING, tick, _travel(LANES[car.approach][2]))
        case Motion.EXITING:
            car.load = 'EMPTY'
            car.begin(Motion.IDLE, tick, rng.randint(*_PAUSES[level]))
        case Motion.WAITING:
            pass


def _sample(
    car: _Car, tick: int, phase: Phase, closed: bool, owner: _Car | None
) -> Sample:
    approach, crossing, exit_edge = LANES[car.approach]
    edge = approach
    progress = 0.0
    reason = None
    blocked_by = None
    if car.motion == Motion.WAITING:
        progress = 1.0
        if not _eligible(car, phase):
            reason = WaitReason.RED
        elif closed:
            reason = WaitReason.BLOCKED_EXIT
        elif owner:
            reason, blocked_by = WaitReason.OCCUPIED, owner.id
        else:
            reason = WaitReason.QUEUE
    elif car.motion == Motion.IDLE:
        if car.passage >= 0:
            edge, progress = exit_edge, 1.0
    else:
        if car.motion == Motion.CROSSING:
            edge = crossing
        elif car.motion == Motion.EXITING:
            edge = exit_edge
        progress = (tick - car.start) / (car.until - car.start)
    return Sample(
        car.id,
        car.approach,
        car.motion,
        edge,
        progress,
        exit_edge.target.id if car.motion != Motion.IDLE else None,
        car.load,
        reason,
        blocked_by,
    )


def simulate(seed: int, duration_seconds: int) -> Trial:
    """Return a reproducible run at 10 Hz; accept seeds [0, 2³¹) and 60–600 seconds."""
    if not 0 <= seed < 2**31 or not 60 <= duration_seconds <= 600:
        raise ValueError(
            'Expected a 31-bit seed and a duration between 60 and 600 seconds.'
        )
    rng = Random(seed)
    level = seed % len(DEMAND_LEVELS)
    duration = duration_seconds * TICKS_PER_SECOND
    signal = Signal(rng.randint(85, 165), rng.randint(85, 165), 15, rng.randrange(230))
    cars = [
        _Car(index, until=rng.randrange(75)) for index in range(1, VEHICLE_COUNT + 1)
    ]
    demand: list[Demand] = []
    passages: list[Passage] = []
    frames: list[Frame] = []
    closed_until = 0
    for tick in range(duration):
        phase, remaining = signal.at(tick)
        if (
            tick % 50 == 0
            and tick >= closed_until
            and rng.random() < (0.07 + 0.07 * level)
        ):
            closed_until = tick + rng.randint(35, 170)
        closed = tick < closed_until
        for car in cars:
            _advance(car, tick, rng, passages, demand, level)
        owner = next((car for car in cars if car.motion == Motion.CROSSING), None)
        if owner is None and not closed:
            waiting = (
                car
                for car in cars
                if car.motion == Motion.WAITING and _eligible(car, phase)
            )
            owner = min(waiting, key=lambda car: (car.start, car.id), default=None)
            if owner:
                owner.begin(Motion.CROSSING, tick, _travel(LANES[owner.approach][1]))
                passages[owner.passage] = replace(
                    passages[owner.passage], grant_tick=tick, entry_tick=tick
                )
        samples = tuple(_sample(car, tick, phase, closed, owner) for car in cars)
        frames.append(Frame(tick, phase, remaining, closed, samples))
    return Trial(
        seed,
        duration,
        DEMAND_LEVELS[level],
        signal,
        tuple(frames),
        tuple(passages),
        tuple(demand),
    )
