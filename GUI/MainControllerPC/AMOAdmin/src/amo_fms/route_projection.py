"""Keep the requested stop separate from the confirmed applied revision."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AppliedRoute:
    """Identity and destination from the server's matched applied-route projection."""

    revision: int
    destination: str


def applied_route(value: dict[str, Any]) -> AppliedRoute | None:
    """Return a revision only when both confirmed fields are valid."""
    revision = value.get('appliedRevisionId')
    destination = value.get('effectiveDestination')
    if isinstance(revision, int) and not isinstance(revision, bool) and revision > 0:
        if isinstance(destination, str) and destination:
            return AppliedRoute(revision, destination)
    return None
