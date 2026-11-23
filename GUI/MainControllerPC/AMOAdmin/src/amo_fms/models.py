"""Fleet preview DTOs and their service-response parsers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from .measurement import sample_identity

OPERATORS = frozenset({'ADMIN', 'OPERATOR'})


def object_value(value: Any) -> dict[str, Any]:
    """Return a decoded object or fail closed on an unexpected response shape."""
    if not isinstance(value, dict):
        raise ValueError('Expected an object.')
    return value


def string_field(data: dict[str, Any], key: str, default: str = '') -> str:
    """Extract a text field without coercing untrusted objects."""
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f'Invalid field {key}.')
    return value


def optional_string(data: dict[str, Any], key: str) -> str:
    """Read optional text, preserving unrelated invalid-field errors."""
    return '' if data.get(key) is None else string_field(data, key)


def optional_number(data: dict[str, Any], key: str) -> float | None:
    """Return a finite reported measurement or no value."""
    value = data.get(key)
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    ):
        return float(value)
    return None


def records(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Read a bounded list of decoded records for a GUI table."""
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f'Invalid list {key}.')
    return [object_value(row) for row in value[:400]]


def identity(data: dict[str, Any], key: str = 'id') -> str:
    """Extract a display-safe opaque string or numeric identifier."""
    raw = data.get(key)
    if isinstance(raw, (str, int)) and not isinstance(raw, bool) and str(raw):
        return str(raw)
    raise ValueError(f'Invalid identifier {key}.')


@dataclass(frozen=True, slots=True)
class Operator:
    """Backend-issued authorization data for the signed-in operator."""

    id: str
    name: str
    email: str
    role: str

    @classmethod
    def parse(cls, value: Any) -> Operator:
        """Parse an operator and reject roles unauthorized for fleet monitoring."""
        user = object_value(value)
        role = string_field(user, 'role')
        if role not in OPERATORS:
            raise PermissionError('Operator role required.')
        return cls(
            identity(user),
            string_field(user, 'name'),
            string_field(user, 'email'),
            role,
        )


@dataclass(frozen=True, slots=True)
class Vehicle:
    """Vehicle identity and reported connection separate from motion state."""

    id: str
    number: str
    status: str
    battery_percent: int | float | None
    connection: str
    stop_reason: str
    position_m: tuple[float, float] | None
    yaw_rad: float | None
    speed_mps: float | None
    dispatch_enabled: bool | None
    sample: tuple[str, int, str] | None = None

    @classmethod
    def parse(cls, value: dict[str, Any]) -> Vehicle:
        """Read recorded position in meters, yaw in radians and speed in m/s."""
        battery = optional_number(value, 'batteryPercent')
        if battery is not None and not 0 <= battery <= 100:
            battery = None
        x, y = optional_number(value, 'xM'), optional_number(value, 'yM')
        dispatch = value.get('dispatchEnabled')
        return cls(
            identity(value),
            string_field(value, 'vehicleNo'),
            string_field(value, 'status'),
            battery,
            string_field(value, 'connection'),
            optional_string(value, 'stopReason'),
            (x, y) if x is not None and y is not None else None,
            optional_number(value, 'yawRad'),
            optional_number(value, 'speedMps'),
            dispatch if isinstance(dispatch, bool) else None,
            sample_identity(value.get('sample')),
        )

    @property
    def connected(self) -> bool:
        """Return whether the backend explicitly reports an active connection."""
        return self.connection.upper() in {'CONNECTED', 'ONLINE', 'NORMAL', 'ACTIVE'}

    @property
    def can_preview(self) -> bool:
        """Allow drafting for a live link or an explicitly simulated link."""
        return self.connected or self.connection.upper() == 'SIMULATED'


@dataclass(frozen=True, slots=True)
class RideRequest:
    """A request identifier and its confirmed operational state."""

    id: str
    pickup: str
    destination: str
    status: str

    @classmethod
    def parse(cls, value: dict[str, Any]) -> RideRequest:
        """Read a request without interpreting acceptance as completed dispatch."""
        return cls(
            identity(value),
            string_field(value, 'pickup'),
            string_field(value, 'destination'),
            string_field(value, 'status'),
        )


@dataclass(frozen=True, slots=True)
class Event:
    """A received event with its original backend event code."""

    id: str
    time: str
    type: str
    vehicle: str
    detail: str

    @classmethod
    def parse(cls, value: dict[str, Any]) -> Event:
        """Preserve the original type and detail for explicit history display."""
        return cls(
            identity(value),
            string_field(value, 'time'),
            string_field(value, 'type'),
            optional_string(value, 'vehicle'),
            optional_string(value, 'detail'),
        )


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Immutable backend preview snapshot shown without inferring telemetry."""

    vehicles: tuple[Vehicle, ...] = ()
    requests: tuple[RideRequest, ...] = ()
    events: tuple[Event, ...] = ()
    demo: bool = False

    @classmethod
    def parse(cls, value: Any) -> Snapshot:
        """Read complete data sets and never promote local drafts to vehicle data."""
        data = object_value(value)
        return cls(
            tuple(Vehicle.parse(row) for row in records(data, 'vehicles')),
            tuple(RideRequest.parse(row) for row in records(data, 'requests')),
            tuple(Event.parse(row) for row in records(data, 'events')),
            data.get('demo') is True,
        )
