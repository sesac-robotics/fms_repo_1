"""Translate an immutable simulation run to normalized recording rows."""

from collections.abc import Iterator
from functools import partial
from itertools import groupby
from uuid import UUID

from .road_graph import MAP_VERSION
from .trial import Frame, Sample, Trial

type Row = tuple[object, ...]


def telemetry(run: UUID, trial: Trial) -> Iterator[Row]:
    """Emit one synthetic metre position per vehicle per elapsed 100 ms tick."""
    for frame in trial.frames:
        for sample in frame.samples:
            yield (
                run,
                MAP_VERSION,
                sample.vehicle_id,
                frame.tick,
                *sample.edge.pose(sample.progress),
                sample.edge.id,
                sample.progress,
                sample.edge.source.id
                if sample.progress == 0
                else (sample.edge.target.id if sample.progress == 1 else None),
                sample.goal_node_id,
                sample.load_state,
                sample.motion.value,
            )


def _motion_key(
    sample: Sample,
) -> tuple[str, str, str | None, str, str | None, int | None]:
    return (
        sample.motion.value,
        sample.edge.id,
        sample.goal_node_id,
        sample.load_state,
        sample.wait_reason.value if sample.wait_reason else None,
        sample.blocked_by,
    )


def _frame_motion(
    index: int, frame: Frame
) -> tuple[str, str, str | None, str, str | None, int | None]:
    return _motion_key(frame.samples[index])


def motions(run: UUID, trial: Trial) -> Iterator[Row]:
    """Coalesce consecutive motion and reason states into half-open tick intervals."""
    for index in range(len(trial.frames[0].samples)):
        for key, frames in groupby(trial.frames, partial(_frame_motion, index)):
            interval = tuple(frames)
            first, last = interval[0], interval[-1]
            yield (
                run,
                MAP_VERSION,
                first.samples[index].vehicle_id,
                first.tick,
                last.tick + 1,
                *key,
            )


def signals(run: UUID, trial: Trial) -> Iterator[Row]:
    """Coalesce observed signal and exit availability into half-open intervals."""
    for key, frames in groupby(trial.frames, lambda f: (f.phase.value, f.exit_closed)):
        interval = tuple(frames)
        first, last = interval[0], interval[-1]
        yield run, first.tick, last.tick + 1, *key
