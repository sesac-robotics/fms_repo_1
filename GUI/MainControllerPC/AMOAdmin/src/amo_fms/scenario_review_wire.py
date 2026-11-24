"""Parse and transport the local scenario review contract over the staff HTTP session."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

from .models import object_value, records, string_field
from .staff_api import StaffApi

ROOT = '/api/admin/demo/scenarios'


def _steps(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not all(
        isinstance(x, str) and x.isascii() and x.replace('_', '').isalpha() for x in raw
    ):
        raise ValueError('Invalid step names.')
    return tuple(raw)


@dataclass(frozen=True, slots=True)
class Plan:
    """Server-defined order and the steps that accept manual Android evidence."""

    id: str
    steps: tuple[str, ...]
    manual_steps: tuple[str, ...]

    @classmethod
    def parse(cls, data: dict[str, Any]) -> Plan:
        """Read one catalog item with stable ordered step names."""
        return cls(
            string_field(data, 'id'),
            _steps(data.get('steps')),
            _steps(data.get('manualSteps')),
        )


@dataclass(frozen=True, slots=True)
class Run:
    """Committed observations and the next permitted server action."""

    id: UUID
    plan: str
    vehicle_number: str
    request_id: int | None
    next_step: str | None
    completed: dict[str, dict[str, Any]]

    @classmethod
    def parse(cls, data: dict[str, Any]) -> Run:
        """Read a snapshot scoped by its run and optional positive request ID."""
        request = data.get('requestId')
        if request is not None and (type(request) is not int or request <= 0):
            raise ValueError('Invalid request ID.')
        next_step = data.get('nextStep')
        if next_step is not None:
            next_step = _steps([next_step])[0]
        return cls(
            UUID(string_field(data, 'id')),
            string_field(data, 'plan'),
            string_field(data, 'vehicleNumber'),
            request,
            next_step,
            {
                string_field(item, 'step'): object_value(item.get('evidence'))
                for item in records(data, 'completed')
            },
        )


class ReviewHttp(QObject):
    """Own one in-flight review request and return bounded server JSON."""

    received = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, api: StaffApi, parent: QObject) -> None:
        """Use the authenticated staff API and its existing gateway timeout."""
        super().__init__(parent)
        self._api = api
        self._reply: QNetworkReply | None = None

    def send(
        self, operation: str, suffix: str = '', body: dict[str, Any] | None = None
    ) -> None:
        """Start one GET or JSON POST without blocking the Admin UI thread."""
        reply = self._api.web_request(ROOT + suffix, body, authenticated=True)
        self._reply = reply
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._finish(operation, reply))

    def _finish(self, operation: str, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply is not self._reply:
            return
        self._reply = None
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        try:
            if reply.bytesAvailable() > 200_000:
                raise ValueError('Review response too large.')
            data = object_value(json.loads(bytes(reply.readAll())))
        except (ValueError, TypeError):
            data = {}
        if status == 200 and data:
            self.received.emit(operation, data)
        else:
            code = data.get('code')
            self.failed.emit(
                code
                if isinstance(code, str) and code
                else 'SCENARIO_SERVICE_UNAVAILABLE'
            )
