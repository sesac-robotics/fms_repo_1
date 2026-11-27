"""Author simulated Taxi paths on the confirmed 2306 by 2103 road artwork."""

from __future__ import annotations

from math import dist

from .review_playback import Checkpoint

type Point = tuple[float, float]
type Path = tuple[Point, ...]

# These illustration coordinates use an 800 by 730 reference image, top-left origin.
# They represent neither measured world coordinates nor vehicle commands.
BOARD = (800, 730)
DEPOT = (211.0, 466.0)
STAGING = (287.0, 466.0)
PICKUP = (172.0, 334.0)
EN_ROUTE = (365.0, 188.0)
WAIT = (365.0, 245.0)
S2 = (588.0, 334.0)
S4 = (638.0, 460.0)
EXIT = (357.0, 692.0)
WEST = (40.0, 692.0)

_TO_PICKUP: Path = ((350, 466), (371, 445), (371, 350), (356, 334), PICKUP)
_TO_WAIT: Path = (
    (53, 334),
    (40, 320),
    (40, 50),
    (55, 33),
    (350, 33),
    (365, 50),
    EN_ROUTE,
)
_TO_S4: Path = ((365, 435), (393, 460), S4)
_TO_S2: Path = (*_TO_S4, (742, 460), (761, 440), (761, 355), (740, 334), S2)
_WEST_TO_DEPOT: Path = (WEST, (40, 490), (64, 466), DEPOT)
_RETURN_FROM_S2: Path = ((392, 334), (364, 358), (364, 670), EXIT, *_WEST_TO_DEPOT)
_RETURN_FROM_S4: Path = (
    (746, 460),
    (761, 485),
    (761, 672),
    (735, 692),
    EXIT,
    *_WEST_TO_DEPOT,
)


def movements(checkpoints: tuple[Checkpoint, ...]) -> tuple[Path, ...]:
    """Return a path per committed stage, beginning at the shared depot position."""
    point = DEPOT
    route_applied = False
    result: list[Path] = []
    waypoints: Path
    for event in checkpoints:
        if event.step == 'ROUTE_APPLIED':
            route_applied = True
        match event.step:
            case 'INITIAL_VACATE':
                waypoints = (STAGING,)
            case 'ASSIGN':
                waypoints = _TO_PICKUP
            case 'DEPART':
                waypoints = _TO_WAIT
            case 'STOP_WAIT' | 'RESUME_APPROVED' | 'CHANGE_PROPOSE' if (
                point == EN_ROUTE
            ):
                waypoints = (WAIT,)
            case 'REDEPART' | 'DESTINATION_STOP' if point == WAIT:
                waypoints = _TO_S4 if route_applied else _TO_S2
            case 'RETURN_ARRIVAL':
                waypoints = _RETURN_FROM_S4 if point == S4 else _RETURN_FROM_S2
            case 'RETURN_VACATE':
                waypoints = (STAGING,)
            case _:
                waypoints = ()
        result.append((point, *waypoints))
        if waypoints:
            point = waypoints[-1]
    return tuple(result)


def along(path: Path, progress: float) -> Point:
    """Interpolate by distance across all segments at progress in [0, 1]."""
    segments = tuple(zip(path, path[1:], strict=False))
    lengths = tuple(dist(start, end) for start, end in segments)
    travel = max(0.0, min(1.0, progress)) * sum(lengths)
    for (start, end), length in zip(segments, lengths, strict=True):
        if 0 < length >= travel:
            fraction = travel / length
            return (
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            )
        travel -= length
    return path[-1]
