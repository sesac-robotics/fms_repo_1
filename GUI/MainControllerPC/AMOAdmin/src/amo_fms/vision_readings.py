"""Decode and display the optional latest Vision observations in a staff snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import Text, display_time

_SOURCES = {'DRIVING_PERCEPTION', 'TRAFFIC_RULES', 'DIRECTION_RECOGNITION'}
_OUTCOMES = {'DETECTED', 'NOT_DETECTED', 'UNAVAILABLE'}


@dataclass(frozen=True, slots=True)
class VisionReading:
    """One detector outcome with frame identity and ISO-8601 UTC timestamps."""

    vehicle: str
    source: str
    frame: str
    captured_at: str
    received_at: str
    outcome: str
    label: str

    def summary(self, tr: Text) -> str:
        """Show the latest classification and its source capture time."""
        status = tr(f'vision_{self.outcome.lower()}')
        if self.label:
            status = f'{status} ({self.label})'
        return f'{self.source} · {status} · {display_time(self.captured_at)}'

    def admin_summary(self, tr: Text) -> str:
        """Show a current result's vehicle, frame and server reception time."""
        return (
            f'{tr("vision_reading")} · {self.vehicle} · {self.summary(tr)}'
            f' · {self.frame} · {display_time(self.received_at)}'
        )


def parse_vision(value: object) -> tuple[VisionReading, ...]:
    """Read optional rows and keep fleet data usable if a row is absent or invalid."""
    if not isinstance(value, list):
        return ()
    readings: list[VisionReading] = []
    for row in value[:400]:
        if not isinstance(row, dict) or not isinstance(row.get('observation'), dict):
            continue
        item = row['observation']
        codes = (
            item.get('vehicleNo'),
            item.get('source'),
            item.get('frameId'),
            item.get('capturedAt'),
            row.get('receivedAt'),
            item.get('outcome'),
            '' if item.get('label') is None else item['label'],
        )
        if not all(isinstance(field, str) for field in codes):
            continue
        reading = VisionReading(*codes)
        if reading.source in _SOURCES and reading.outcome in _OUTCOMES:
            readings.append(reading)
    return tuple(readings)


def vehicle_vision_summary(
    readings: tuple[VisionReading, ...], vehicle: str, tr: Text
) -> str:
    """Format the selected vehicle's observations or show that none exist."""
    return '\n'.join(v.summary(tr) for v in readings if v.vehicle == vehicle) or tr(
        'vision_no_report'
    )
