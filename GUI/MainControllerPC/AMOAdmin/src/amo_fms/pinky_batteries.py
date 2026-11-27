"""Render device-level battery observations independently of fleet vehicles."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .i18n import Text


@dataclass(frozen=True, slots=True)
class PinkyBattery:
    """Equipment ID and optional battery readings in percent and volts."""

    device_id: str
    percent: float | None
    voltage: float | None
    simulated: bool

    def summary(self, tr: Text) -> str:
        """Display both measurements and identify simulated readings."""
        readings = (
            f'{self.percent:g}% · {self.voltage:g} V'
            if self.percent is not None and self.voltage is not None
            else '—'
        )
        suffix = f' · {tr("pinky_simulated")}' if self.simulated else ''
        return f'{self.device_id} · {readings}{suffix}'


def _measurement(value: object, maximum: int) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 0 <= value <= maximum:
            return float(value)
    return None


def parse_pinky_batteries(value: object) -> tuple[PinkyBattery, ...]:
    """Accept optional equipment data without breaking older snapshots."""
    if not isinstance(value, list):
        return ()
    readings = []
    for row in value[:32]:
        if not isinstance(row, dict):
            continue
        device_id = row.get('deviceId')
        if not isinstance(device_id, str) or not re.fullmatch(
            r'PP_[0-9]{5}', device_id
        ):
            continue
        readings.append(
            PinkyBattery(
                device_id,
                _measurement(row.get('percent'), 100),
                _measurement(row.get('voltage'), 20),
                row.get('simulated') is True,
            )
        )
    return tuple(readings)
