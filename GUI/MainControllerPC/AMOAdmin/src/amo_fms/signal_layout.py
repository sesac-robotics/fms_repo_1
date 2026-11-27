"""Where each signal's masts stand on the confirmed board (800 x 730 review units)."""

from __future__ import annotations

from dataclasses import dataclass

type Point = tuple[float, float]


@dataclass(frozen=True)
class Mast:
    """A mast-arm signal: a pole on the island and a head hanging over the road.

    The head lies along the arm, which is across the lanes it controls, so the
    driver sees it horizontal: a west-pointing arm draws a horizontal head on
    the map, a north-pointing arm a vertical one. The pole stands at the
    driver's right, so red, at the driver's left, is the lamp farthest from it.
    """

    pole: Point
    head: Point
    pedestrian: bool = False  # a two-lamp head on a short post by the crosswalk
    # A pole at the driver's left (no island at the far-right corner): red is
    # then the lamp nearest the pole.
    red_at_pole: bool = False

    @property
    def horizontal(self) -> bool:
        """Whether the head is drawn horizontally on the map."""
        return abs(self.head[0] - self.pole[0]) >= abs(self.head[1] - self.pole[1])

    @property
    def reverse(self) -> bool:
        """Whether red sits at the right or bottom end, away from a west/north pole."""
        axis = 0 if self.horizontal else 1
        return (self.head[axis] > self.pole[axis]) != self.red_at_pole


@dataclass(frozen=True)
class Intersection:
    """One signal's two masts and click area, in the 800 x 730 units of review_lanes."""

    signal_id: str
    a: Mast  # head a, lit in NORTH_* phases
    b: Mast  # head b, lit in EAST_* phases
    area: tuple[float, float, float, float]  # left, top, right, bottom


# The north T-junction. SIG-03 stands at its south-east corner: head b hangs
# over the eastbound lanes of the top road, head a is the pedestrian signal
# seen by people crossing the north arm from west to east. SIG-04 mirrors it at
# the south-west corner for westbound cars and people crossing east to west;
# the top road has no island on its north side, so that car pole stands at the
# driver's left. Both boards show identical signals.
_NORTH_T = (300, 0, 492, 122)

# The centre "+" intersection of the confirmed board, served by two boards.
# Each pole stands on the yellow island at the far-right corner seen by the
# drivers it serves, with the arm reaching over their lanes. SIG-01:
# northbound from the north-east corner, eastbound from the south-east.
# SIG-02 mirrors it through the centre: southbound from the south-west,
# westbound from the north-west. Add rows as more signals are installed.
_CENTRE = (332, 304, 460, 496)
INTERSECTIONS = (
    Intersection(
        'SIG-01',
        a=Mast(pole=(483.0, 220.0), head=(427.0, 220.0)),
        b=Mast(pole=(481.0, 519.0), head=(481.0, 462.0)),
        area=_CENTRE,
    ),
    Intersection(
        'SIG-02',
        a=Mast(pole=(309.0, 580.0), head=(365.0, 580.0)),
        b=Mast(pole=(311.0, 281.0), head=(311.0, 338.0)),
        area=_CENTRE,
    ),
    Intersection(
        'SIG-03',
        a=Mast(pole=(474.0, 122.0), head=(474.0, 100.0), pedestrian=True),
        b=Mast(pole=(486.0, 84.0), head=(486.0, 34.0)),
        area=_NORTH_T,
    ),
    Intersection(
        'SIG-04',
        a=Mast(pole=(319.0, 122.0), head=(319.0, 100.0), pedestrian=True),
        b=Mast(pole=(307.0, 84.0), head=(307.0, 34.0), red_at_pole=True),
        area=_NORTH_T,
    ),
)
