"""Extract finite measurements and opaque identities from decoded service data."""

from math import isfinite
from typing import Any


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


def identity(data: dict[str, Any], key: str = 'id') -> str:
    """Extract a display-safe opaque string or numeric identifier."""
    raw = data.get(key)
    if isinstance(raw, (str, int)) and not isinstance(raw, bool) and str(raw):
        return str(raw)
    raise ValueError(f'Invalid identifier {key}.')
