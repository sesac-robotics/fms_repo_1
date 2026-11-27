"""Build leakage-free features, deterministic baseline and observed labels in seconds."""

from collections import Counter
from dataclasses import dataclass
from math import ceil

from .road_graph import LANES, Approach
from .trial import TICKS_PER_SECOND, Frame, Motion, Passage, Phase, Signal, Trial

HORIZONS = (10, 30)
FEATURE_NAMES = (
    'north_queue',
    'east_queue',
    'north_approaching',
    'east_approaching',
    'occupied',
    'exit_closed',
    'north_green',
    'east_green',
    'phase_remaining',
    'north_green_duration',
    'east_green_duration',
)


@dataclass(frozen=True)
class Outcome:
    """Vehicle queue size and seconds until the next currently waiting vehicle is granted."""

    queue: float
    wait_s: float


@dataclass(frozen=True)
class Example:
    """One cutoff and horizon; only label reads the future observed simulation."""

    seed: int
    tick: int
    horizon_s: int
    features: tuple[float, ...]
    baseline: Outcome
    label: Outcome


def _state(frame: Frame, signal: Signal) -> tuple[float, ...]:
    counts = Counter((s.motion, s.approach) for s in frame.samples)
    return (
        counts[Motion.WAITING, Approach.NORTH],
        counts[Motion.WAITING, Approach.EAST],
        counts[Motion.APPROACHING, Approach.NORTH],
        counts[Motion.APPROACHING, Approach.EAST],
        any(s.motion == Motion.CROSSING for s in frame.samples),
        frame.exit_closed,
        frame.phase == Phase.NORTH,
        frame.phase == Phase.EAST,
        frame.phase_remaining / 100,
        signal.north / 100,
        signal.east / 100,
    )


def baseline(frame: Frame, signal: Signal, horizon_s: int) -> Outcome:
    """Project the observed queue with the known signal plan and no new arrivals."""
    queues = Counter(s.approach for s in frame.samples if s.motion == Motion.WAITING)
    crossing_ticks = {
        approach: ceil(TICKS_PER_SECOND * lane[1].length_m / lane[1].speed_limit_mps)
        for approach, lane in LANES.items()
    }
    remaining = max(
        (
            ceil((1 - s.progress) * crossing_ticks[s.approach])
            for s in frame.samples
            if s.motion == Motion.CROSSING
        ),
        default=0,
    )
    release = frame.tick + max(
        1, remaining, TICKS_PER_SECOND if frame.exit_closed else 0
    )
    target = frame.tick + horizon_s * TICKS_PER_SECOND
    size = 0
    for tick in range(
        frame.tick + 1, target + 2 * (signal.north + signal.east + 2 * signal.all_red)
    ):
        phase, _ = signal.at(tick)
        direction = {Phase.NORTH: Approach.NORTH, Phase.EAST: Approach.EAST}.get(phase)
        if direction is not None and queues[direction] and tick >= release:
            if tick > target:
                return Outcome(size, (tick - target) / TICKS_PER_SECOND)
            queues[direction] -= 1
            release = tick + crossing_ticks[direction]
        if tick == target:
            size = queues.total()
            if not size:
                return Outcome(0, 0)
    raise AssertionError('A queued vehicle had no scheduled phase')


def _observed(passages: tuple[Passage, ...], target: int) -> Outcome | None:
    waiting = [
        item
        for item in passages
        if item.request_tick <= target
        and (item.grant_tick is None or item.grant_tick > target)
    ]
    if not waiting:
        return Outcome(0, 0)
    first = min(
        (item.grant_tick for item in waiting if item.grant_tick is not None),
        default=None,
    )
    if first is None:
        return None
    return Outcome(len(waiting), (first - target) / TICKS_PER_SECOND)


def examples(trial: Trial) -> tuple[Example, ...]:
    """Sample every two seconds, dropping targets censored by the run boundary."""
    rows = []
    for frame in trial.frames[:: 2 * TICKS_PER_SECOND]:
        for horizon in HORIZONS:
            target = frame.tick + horizon * TICKS_PER_SECOND
            if target >= trial.duration_ticks:
                continue
            observed = _observed(trial.passages, target)
            if observed is not None:
                rows.append(
                    Example(
                        trial.seed,
                        frame.tick,
                        horizon,
                        _state(frame, trial.signal),
                        baseline(frame, trial.signal, horizon),
                        observed,
                    )
                )
    return tuple(rows)
