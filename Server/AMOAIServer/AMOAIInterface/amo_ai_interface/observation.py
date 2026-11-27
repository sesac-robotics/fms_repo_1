"""Validate detector results and translate them into AMO staff observations."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from amo_ai_interface.frame import NS_PER_SECOND, Frame

Outcome = Literal['DETECTED', 'NOT_DETECTED', 'UNAVAILABLE']

_LABEL = re.compile(r'[A-Z0-9_]{1,40}')
_UTC_TIME = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z')
_REQUIRED = {'frame_id', 'outcome', 'processed_at'}
_ALLOWED = _REQUIRED | {'label', 'confidence'}
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Detection:
    """One validated detector response correlated to a requested camera frame."""

    outcome: Outcome
    processed_at: datetime
    label: str | None
    confidence: float | None


def _capture_time(frame: Frame) -> datetime:
    seconds, nanoseconds = divmod(frame.stamp_ns, NS_PER_SECOND)
    return _EPOCH + timedelta(seconds=seconds, microseconds=nanoseconds // 1000)


def parse_detection(value: object, frame: Frame) -> Detection:
    """Read the detector JSON, raising ValueError on an invalid or mock response.

    The detector echoes the request frame ID and provides the UTC processing
    time in ISO 8601 at up to microsecond precision. Processing cannot precede
    the publisher's frame time.
    """
    if (
        not isinstance(value, dict)
        or not _REQUIRED <= value.keys() <= _ALLOWED
        or value['frame_id'] != frame.frame_id
    ):
        raise ValueError('Unexpected detector response or frame ID')
    stamp = value['processed_at']
    if not isinstance(stamp, str) or _UTC_TIME.fullmatch(stamp) is None:
        raise ValueError('Expected an ISO 8601 UTC processing time ending in Z')
    processed_at = datetime.fromisoformat(stamp)
    if processed_at < _capture_time(frame):
        raise ValueError('Processing precedes camera capture')
    outcome = value['outcome']
    if outcome in ('NOT_DETECTED', 'UNAVAILABLE'):
        if {'label', 'confidence'} & value.keys():
            raise ValueError('Only a detection may include a label or confidence')
        return Detection(outcome, processed_at, None, None)
    if outcome != 'DETECTED':
        raise ValueError('Unknown detector outcome')

    label = value.get('label')
    if not isinstance(label, str) or _LABEL.fullmatch(label) is None:
        raise ValueError('A detection needs an uppercase label')
    confidence = value.get('confidence')
    if 'confidence' in value and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (float, int))
        or not 0 <= confidence <= 1
    ):
        raise ValueError('Detector confidence must be a number between 0 and 1')
    return Detection('DETECTED', processed_at, label, confidence)


def observation_payload(
    frame: Frame, detection: Detection, vehicle_no: str, source: str, result_id: UUID
) -> dict[str, str | float]:
    """Build the Main Control fields using the caller's ID and vehicle mapping.

    Both timestamps use UTC, truncated to PostgreSQL microsecond precision.
    The payload contains only the metadata accepted by the observation API.
    """
    payload: dict[str, str | float] = {
        'resultId': str(result_id),
        'vehicleNo': vehicle_no,
        'source': source,
        'frameId': frame.frame_id,
        'capturedAt': _capture_time(frame).isoformat().replace('+00:00', 'Z'),
        'processedAt': detection.processed_at.isoformat().replace('+00:00', 'Z'),
        'outcome': detection.outcome,
    }
    if detection.label is not None:
        payload['label'] = detection.label
    if detection.confidence is not None:
        payload['confidence'] = detection.confidence
    return payload
