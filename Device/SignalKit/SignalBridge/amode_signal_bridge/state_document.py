"""Decode the firmware's JSON state message before it is forwarded.

Only the JSON shape is checked here. Main Control validates the fields and
answers 400 for an inconsistent report, so the bridge does not duplicate the
business rules.
"""

from __future__ import annotations

import json


def parse_state(text: str) -> dict[str, object] | None:
    """Return the decoded object, or None when the text is not a JSON object."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None
