"""UI catalogs and backend terminology display."""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from zoneinfo import ZoneInfo

ALIAS = {
    'ONLINE': 'status_connected',
    'NORMAL': 'status_connected',
    'CONNECTED': 'status_connected',
    'OFFLINE': 'status_disconnected',
    'LOST': 'status_disconnected',
    'DISCONNECTED': 'status_disconnected',
    'WAITING_AT_STOP': 'status_waiting',
    'WAITING_FOR_DISPATCH': 'status_pending',
    'WAITING_DISPATCH': 'status_pending',
    'QUEUED': 'status_pending',
    'PENDING': 'status_pending',
    'EN_ROUTE': 'status_driving',
    'IN_PROGRESS': 'status_driving',
    'IN_SERVICE': 'status_driving',
    'IN_TRANSIT': 'status_driving',
    'MOVING': 'status_driving',
    'DRIVING': 'status_driving',
    'REQUESTED': 'status_received',
    'REQUEST_RECEIVED': 'status_received',
    'REQUEST_ACCEPTED': 'request_event',
    'COMMAND_ACCEPTED': 'request_event',
    'VEHICLE_OBSERVED': 'observed_event',
    'VEHICLE_STATE': 'observed_event',
    'DISPATCHED': 'status_assigned',
    'CANCELED': 'status_cancelled',
    'STOPPED_OBSERVED': 'status_stopped',
    'PICKUP_EN_ROUTE': 'status_pickup',
    'ADMIN': 'role_admin',
    'OPERATOR': 'role_operator',
}

EVENT_DETAILS = {
    'Fictional completed trip': 'detail_demo_completed',
    'Fictional loss of link': 'detail_demo_link_lost',
    'Fictional request waits for an eligible vehicle': 'detail_demo_waiting',
    'Passenger request received': 'detail_passenger_received',
}


@lru_cache(maxsize=3)
def catalog(language: str) -> dict[str, str]:
    """Load a static UI locale bundled with the FMS."""
    selected = language if language in {'ko', 'en', 'zh-Hans'} else 'ko'
    return json.loads(
        files('amo_fms')
        .joinpath('translations', f'{selected}.json')
        .read_text(encoding='utf-8')
    )


class Text:
    """Translate stable UI keys and preserve unknown backend values as evidence."""

    def __init__(self, language: str) -> None:
        """Keep the current locale without changing global Qt settings."""
        self.language = language

    def __call__(self, key: str, **values: str | int) -> str:
        """Translate a UI key and interpolate application-owned arguments."""
        template = catalog(self.language).get(key, catalog('en').get(key, key))
        return template.format(**values)

    def status(self, value: str) -> str:
        """Translate known codes while leaving site-defined values visible."""
        if not value:
            return self('unknown')
        code = re.sub(r'[^A-Z0-9]+', '_', value.upper()).strip('_')
        key = ALIAS.get(code, f'status_{code.lower()}')
        return self(key) if key in catalog('en') else value

    def event_detail(self, raw: str) -> str:
        """Localize known server messages and retain unknown evidence verbatim."""
        key = EVENT_DETAILS.get(raw)
        return self(key) if key is not None else (raw or '—')


def display_time(raw: str) -> str:
    """Format an ISO-8601 event in Seoul time, preserving non-ISO backend labels."""
    if not raw:
        return '—'
    try:
        stamp = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return raw
    if stamp.tzinfo is None:
        return raw
    return stamp.astimezone(ZoneInfo('Asia/Seoul')).strftime('%m-%d %H:%M:%S')
