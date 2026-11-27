"""Versioned directed schematic for one intersection on the confirmed AMO drawing."""

from dataclasses import dataclass
from enum import StrEnum
from math import dist

MAP_SHA256 = '5a5a468f9aea331a7efb9c798d70235d4b3ae60b73cd24cfe1198a08f7c716d4'
MAP_VERSION = 'confirmed-pilot-v1'
FRAME_ID = 'confirmed_pilot_xy'
INTERSECTION_ID = 'central-crossing'
IMAGE_ANCHOR = (365 / 800, 334 / 730)
_METRES_PER_DRAWING_PIXEL = 0.003


class Approach(StrEnum):
    """Direction of approach from the north or from the east."""

    NORTH = 'NORTH'
    EAST = 'EAST'


@dataclass(frozen=True)
class Node:
    """A stable directed-graph node in synthetic metres, origin at drawing top left."""

    id: str
    kind: str
    x_m: float
    y_m: float


@dataclass(frozen=True)
class Edge:
    """Directed traversal from source to target with a synthetic speed limit in m/s."""

    id: str
    source: Node
    target: Node
    speed_limit_mps: float
    intersection: bool = False

    @property
    def length_m(self) -> float:
        """Return Euclidean length in the synthetic map frame."""
        return dist(
            (self.source.x_m, self.source.y_m), (self.target.x_m, self.target.y_m)
        )

    def pose(self, progress: float) -> tuple[float, float]:
        """Interpolate a position in synthetic metres at a fraction in [0, 1]."""
        x, y = self.source.x_m, self.source.y_m
        return (
            x + progress * (self.target.x_m - x),
            y + progress * (self.target.y_m - y),
        )


def _node(id: str, kind: str, x_px: int, y_px: int) -> Node:
    return Node(
        id, kind, x_px * _METRES_PER_DRAWING_PIXEL, y_px * _METRES_PER_DRAWING_PIXEL
    )


def _lane(
    approach: Approach, points: tuple[tuple[int, int], ...]
) -> tuple[Edge, Edge, Edge]:
    name = approach.value.lower()
    start, stop, clear, target = (
        _node(f'{name}-{kind}', kind, *point)
        for kind, point in zip(
            ('entry', 'stop-line', 'clearance', 'goal'), points, strict=True
        )
    )
    return (
        Edge(f'{name}-approach', start, stop, 0.35),
        Edge(f'{name}-crossing', stop, clear, 0.20, True),
        Edge(f'{name}-exit', clear, target, 0.35),
    )


LANES = {
    Approach.NORTH: _lane(
        Approach.NORTH, ((365, 145), (365, 300), (365, 383), (365, 610))
    ),
    Approach.EAST: _lane(
        Approach.EAST, ((700, 334), (475, 334), (310, 334), (130, 334))
    ),
}
