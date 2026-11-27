"""Optional JSON Lines observations for the local FMS comparison."""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import monotonic_ns, time_ns
from typing import Any


def observe(event: str, **fields: Any) -> None:
    """Append a UTC and monotonic nanosecond observation to AMO_FMS_TRACE."""
    if destination := os.environ.get('AMO_FMS_TRACE'):
        row = dict(event=event, utc_ns=time_ns(), monotonic_ns=monotonic_ns(), **fields)
        with Path(destination).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row) + '\n')


def sample_identity(value: object) -> tuple[str, int, str] | None:
    """Read an optional epoch, sequence and ISO server reception time."""
    if not isinstance(value, dict):
        return None
    epoch = value.get('epoch')
    sequence = value.get('sequence')
    received = value.get('receivedAt')
    if isinstance(epoch, str) and type(sequence) is int and isinstance(received, str):
        return epoch, sequence, received
    return None
