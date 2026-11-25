"""Validate a bounded offline congestion replay against the selected map image."""

import json
from dataclasses import dataclass
from hashlib import file_digest
from math import isfinite
from pathlib import Path
from uuid import UUID

_MAX_BYTES = 1_048_576
_HORIZONS = {10, 30}


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError('Expected a congestion object.')
    return value


def _number(value: object, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Invalid congestion value.')
    if not 0 <= value <= maximum or not isfinite(value):
        raise ValueError('Congestion value outside limits.')
    return float(value)


@dataclass(frozen=True)
class Outcome:
    """Queue count and next grant delay, in vehicles and seconds respectively."""

    queue: float
    wait_s: float

    @classmethod
    def parse(cls, raw: object) -> 'Outcome':
        """Validate a model, baseline or observed value for a four-vehicle replay."""
        data = _object(raw)
        return cls(_number(data.get('queue'), 4), _number(data.get('wait_s'), 600))


@dataclass(frozen=True)
class Forecast:
    """Three comparable outcomes at a single prediction horizon in seconds."""

    horizon_s: int
    model: Outcome
    baseline: Outcome
    observed: Outcome


@dataclass(frozen=True)
class Trace:
    """Read-only experiment rows grouped by elapsed 100 ms tick."""

    run_id: UUID
    intersection: str
    anchor: tuple[float, float]
    frames: tuple[tuple[int, tuple[Forecast, ...]], ...]

    @classmethod
    def read(cls, source: Path, map_path: Path) -> 'Trace':
        """Return a version 1 trace or raise on missing, mismatched or invalid files."""
        with source.open('rb') as stream:
            payload = stream.read(_MAX_BYTES + 1)
        if len(payload) > _MAX_BYTES:
            raise ValueError('Congestion replay is too large.')
        try:
            data = _object(json.loads(payload))
        except RecursionError as error:
            raise ValueError('Invalid congestion replay nesting.') from error
        if (
            type(data.get('version')) is not int
            or data['version'] != 1
            or data.get('kind') != 'synthetic-intersection-replay'
            or data.get('vehicle_count') != 4
            or data.get('ticks_per_second') != 10
        ):
            raise ValueError('Unsupported congestion replay.')
        with map_path.open('rb') as image:
            if data.get('map_sha256') != file_digest(image, 'sha256').hexdigest():
                raise ValueError('Congestion replay map does not match.')
        run, intersection, anchor = (
            data.get('run_id'),
            data.get('intersection_id'),
            data.get('image_anchor'),
        )
        if (
            not isinstance(run, str)
            or not isinstance(intersection, str)
            or not 1 <= len(intersection) <= 80
            or not isinstance(anchor, list)
            or len(anchor) != 2
        ):
            raise ValueError('Invalid congestion replay identity.')
        return cls(
            UUID(run),
            intersection,
            (_number(anchor[0], 1), _number(anchor[1], 1)),
            _frames(data.get('forecasts')),
        )


def _frames(values: object) -> tuple[tuple[int, tuple[Forecast, ...]], ...]:
    if not isinstance(values, list) or not 1 <= len(values) <= 600:
        raise ValueError('Invalid congestion replay size.')
    frames: dict[int, dict[int, Forecast]] = {}
    for value in values:
        data = _object(value)
        tick, horizon = data.get('tick'), data.get('horizon_s')
        if (
            type(tick) is not int
            or not 0 <= tick < 6000
            or type(horizon) is not int
            or horizon not in _HORIZONS
        ):
            raise ValueError('Invalid congestion forecast time.')
        group = frames.setdefault(tick, {})
        if horizon in group:
            raise ValueError('Duplicate forecast horizon.')
        group[horizon] = Forecast(
            horizon,
            Outcome.parse(data.get('model')),
            Outcome.parse(data.get('baseline')),
            Outcome.parse(data.get('observed')),
        )
    return tuple(
        (tick, tuple(row[key] for key in sorted(row)))
        for tick, row in sorted(frames.items())
    )
