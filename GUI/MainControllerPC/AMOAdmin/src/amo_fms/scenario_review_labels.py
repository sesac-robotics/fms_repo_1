"""Present review evidence with explicit units, original event codes and localized labels."""

from __future__ import annotations

from typing import Any

from .i18n import Text, display_time
from .models import Event, Snapshot
from .review_playback import Playback

EXPECTED: dict[str, tuple[str, str]] = {
    'INITIAL_OCCUPY': ('SD-07', 'FMS · Admin'),
    'INITIAL_CHARGE': ('SD-07', 'FMS · Admin'),
    'INITIAL_READY': ('SD-07', 'FMS · Admin'),
    'INITIAL_VACATE': ('SD-07', 'FMS · Admin'),
    'CALL': ('SD-01', 'Android · FMS'),
    'QUOTE': ('SD-01', 'Android'),
    'PREPAY_DECLINED': ('SD-01', 'Admin · FMS'),
    'LINK_LOST': ('SD-06', 'Admin · FMS'),
    'LINK_RESTORED': ('SD-06', 'Admin · FMS'),
    'RESUME_APPROVED': ('SD-06', 'Admin · FMS'),
    'PREPAY': ('SD-01', 'Android · Admin'),
    'ASSIGN': ('SD-02', 'Android · FMS'),
    'PICKUP_STOP': ('SD-02', 'Android · FMS'),
    'BOARD': ('SD-03', 'Android · FMS'),
    'DEPART': ('SD-03', 'Android · FMS'),
    'STOP_WAIT': ('SD-09', 'Android · FMS'),
    'CHANGE_PROPOSE': ('SD-09', 'Android'),
    'CHANGE_ACCEPT': ('SD-09', 'Android · Admin'),
    'ROUTE_ISSUE': ('SD-09', 'FMS · Admin'),
    'ROUTE_ACK': ('SD-09', 'FMS · Admin'),
    'ROUTE_APPLIED': ('SD-09', 'Android · FMS · Admin'),
    'ROUTE_FAILED': ('SD-09', 'Android · FMS · Admin'),
    'REDEPART': ('SD-09', 'Android · FMS'),
    'DESTINATION_STOP': ('SD-05', 'Android · FMS'),
    'ALIGHT': ('SD-05', 'Android · Admin'),
    'RETURN_ORDER': ('SD-05', 'FMS · Admin'),
    'RETURN_ARRIVAL': ('SD-05', 'FMS · Admin'),
    'RETURN_OCCUPY': ('SD-07', 'FMS · Admin'),
    'RETURN_CHARGE': ('SD-07', 'FMS · Admin'),
    'RETURN_READY': ('SD-07', 'FMS · Admin'),
    'RETURN_VACATE': ('SD-07', 'FMS · Admin'),
}

_FIELDS = {
    'event': 'event_type',
    'observedAt': 'event_time',
    'tripId': 'review_trip_id',
    'status': 'status',
    'quoteId': 'review_quote_id',
    'paymentStatus': 'review_payment',
    'amountMinor': 'review_amount',
    'deltaMinor': 'review_delta',
    'distanceMeters': 'review_distance',
    'durationSeconds': 'review_duration',
    'proposedDestination': 'review_proposed',
    'effectiveDestination': 'review_effective',
    'revisionId': 'review_revision',
    'commandId': 'review_command',
    'cycleId': 'review_cycle',
    'batteryPercent': 'battery',
    'receiptReference': 'review_receipt',
}


def step_title(tr: Text, step: str) -> str:
    """Return the localized stage name for a stable server step."""
    return tr(f'review_step_{step.lower()}')


def observed_text(tr: Text, evidence: dict[str, Any]) -> str:
    """Render only supplied observation fields and preserve raw codes for inspection."""
    values: list[str] = []
    for key, label in _FIELDS.items():
        value = evidence.get(key)
        if value is None:
            continue
        if key == 'observedAt':
            value = f'{display_time(str(value))} KST ({value})'
        elif key in {'amountMinor', 'deltaMinor'}:
            value = f'{value} {evidence.get("currencyCode", "")}'
        elif key == 'batteryPercent':
            value = f'{value:g}%'
        elif key in {'status', 'event', 'paymentStatus'}:
            translated = tr.status(str(value))
            value = value if str(value) == translated else f'{translated} ({value})'
        values.append(f'{tr(label)} · {value}')
    return '\n'.join(values)


def latest_review_stage(snapshot: Snapshot) -> Event | None:
    """Read the latest committed review stage carried by IF-03."""
    return next((e for e in snapshot.events if e.type.startswith('DEMO_REVIEW_')), None)


def review_vehicle(snapshot: Snapshot, selected: str, follow_review: bool) -> str:
    """Prefer the current demo vehicle in review mode and otherwise keep fleet selection."""
    stage = latest_review_stage(snapshot) if follow_review else None
    if stage is not None:
        selected = next(
            (v.id for v in snapshot.vehicles if v.number == stage.vehicle), selected
        )
    if any(v.id == selected for v in snapshot.vehicles):
        return selected
    return snapshot.vehicles[0].id if snapshot.vehicles else ''


def review_stage_text(tr: Text, review: Playback | None, legacy: Event | None) -> str:
    """Format the current simulated state and reason above the confirmed map."""
    if review is not None:
        parts = [tr('review_tab'), review.vehicle]
        if review.checkpoints:
            checkpoint = review.checkpoints[-1]
            parts.extend(
                (
                    step_title(tr, checkpoint.step),
                    tr.status(checkpoint.status),
                    tr.status(checkpoint.reason),
                )
            )
        else:
            parts.append(tr('review_ready'))
        return ' · '.join(parts)
    if legacy is None:
        return ''
    title = step_title(tr, legacy.type.removeprefix('DEMO_REVIEW_'))
    return f'{tr("review_tab")} · {legacy.vehicle} · {title}'
