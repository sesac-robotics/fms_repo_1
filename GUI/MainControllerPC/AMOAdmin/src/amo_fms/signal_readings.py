"""Decode the optional SignalKit traffic light states in a staff snapshot."""

from __future__ import annotations

from dataclasses import dataclass

PHASES = ('NORTH_GREEN', 'NORTH_YELLOW', 'ALL_RED', 'EAST_GREEN', 'EAST_YELLOW')
_HOLD_TARGETS = {'NORTH_GREEN', 'EAST_GREEN', 'ALL_RED'}
_PLAN_KEYS = ('northGreenMs', 'eastGreenMs', 'yellowMs', 'allRedMs')


@dataclass(frozen=True, slots=True)
class SignalReading:
    """One signal's latest report as stored by Main Control."""

    signal_id: str
    phase: str
    mode: str
    hold_target: str
    remaining_ms: int
    plan_ms: tuple[int, int, int, int]
    plan_pending: bool
    last_command: str
    command_result: str
    received_at: str

    def lamps(self) -> tuple[str, str]:
        """Return the lit lamp ('R', 'Y' or 'G') for the north and east heads."""
        north = {'NORTH_GREEN': 'G', 'NORTH_YELLOW': 'Y'}.get(self.phase, 'R')
        east = {'EAST_GREEN': 'G', 'EAST_YELLOW': 'Y'}.get(self.phase, 'R')
        return north, east

    def plan_text(self) -> str:
        """Show the plan as seconds: north green / east green / yellow / all red."""
        return ' / '.join(f'{value / 1000:g}s' for value in self.plan_ms)


def parse_signals(value: object) -> tuple[SignalReading, ...]:
    """Read optional rows; skip malformed ones so the fleet view stays usable."""
    if not isinstance(value, list):
        return ()
    readings: list[SignalReading] = []
    for row in value[:64]:
        reading = _reading(row)
        if reading is not None:
            readings.append(reading)
    return tuple(readings)


def _reading(row: object) -> SignalReading | None:
    if not isinstance(row, dict) or not isinstance(row.get('state'), dict):
        return None
    state = row['state']
    plan = state.get('plan')
    if not isinstance(plan, dict):
        return None
    plan_ms = tuple(plan.get(key) for key in _PLAN_KEYS)
    texts = (
        state.get('signalId'),
        state.get('phase'),
        state.get('mode'),
        state.get('lastCommand'),
        state.get('commandResult'),
        row.get('receivedAt'),
    )
    hold = state.get('holdTarget')
    remaining = state.get('remainingMs')
    if (
        not all(isinstance(text, str) for text in texts)
        or not all(_count(ms) for ms in plan_ms)
        or not _count(remaining)
        or not isinstance(state.get('planPending'), bool)
        or texts[1] not in PHASES
        or texts[2] not in ('AUTO', 'HOLD')
        or (hold is not None and hold not in _HOLD_TARGETS)
    ):
        return None
    signal_id, phase, mode, last_command, result, received = texts
    return SignalReading(
        signal_id,
        phase,
        mode,
        hold or '',
        remaining,
        plan_ms,  # type: ignore[arg-type]
        state['planPending'],
        last_command,
        result,
        received,
    )


def _count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
