"""Name the direction each signal head serves.

Every board lights head a in NORTH_* phases and head b in EAST_* phases; the
directions differ per board (see Device/SignalKit config.h). Add a row per
installed board.
"""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import Text

DIRECTIONS = {
    'SIG-01': ('north', 'east'),  # a: south -> north, b: west -> east
    'SIG-02': ('south', 'west'),  # a: north -> south, b: east -> west
    'SIG-03': ('walk', 'east'),  # a: pedestrians at the north T, b: west -> east
    'SIG-04': ('walk', 'west'),  # a: same crossing, west end, b: east -> west
}


def head_names(tr: Text, signal_id: str) -> dict[str, str]:
    """Return {'a': ..., 'b': ...} for labels; unknown signals keep the plain letters."""
    pair = DIRECTIONS.get(signal_id)
    if pair is None:
        return {'a': 'a', 'b': 'b'}
    return {head: tr(f'signal_dir_{way}') for head, way in zip('ab', pair, strict=True)}


def is_pedestrian(signal_id: str) -> bool:
    """Whether head a is a two-lamp pedestrian signal."""
    return DIRECTIONS.get(signal_id, ('', ''))[0] == 'walk'


# Intersections shown on the signals page, in display order, with their boards.
JUNCTIONS = (
    ('signal_junction_t', ('SIG-03', 'SIG-04')),
    ('signal_junction_plus', ('SIG-01', 'SIG-02')),
)
OTHER_JUNCTION = 'signal_junction_other'


@dataclass(frozen=True)
class Coordination:
    """How the boards of one junction share a plan (firmware AMO_COORDINATED).

    ``linked`` lists the editor fields every board shares, in PLAN order
    (0 north green, 1 east green, 2 north yellow, 3 all red, 4 east yellow).
    ``east_turns`` means each board has its own east-west slot, so every board
    is told the others' east green plus yellow. ``note`` explains it on screen.
    """

    linked: tuple[int, ...]
    east_turns: bool
    note: str


# Junctions whose boards run on the agent's clock as one controller.
COORDINATED = {
    # North-south green together, then eastbound and westbound one at a time.
    'signal_junction_plus': Coordination((0, 2, 3), True, 'signal_shared_plan'),
    # Both ends of the crossing show identical pedestrian and car signals.
    'signal_junction_t': Coordination((0, 1, 2, 3, 4), False, 'signal_identical_plan'),
}


def junction_key(signal_id: str) -> str:
    """Translation key of the intersection a signal belongs to."""
    for key, members in JUNCTIONS:
        if signal_id in members:
            return key
    return OTHER_JUNCTION
