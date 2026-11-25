"""Coordinate review session recovery and ordered prefix replay in AMO Admin."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .models import object_value, records
from .scenario_review_wire import Plan, ReviewHttp, Run
from .staff_api import StaffApi

MAP_PREDECESSOR_HOLD_MS = 2200


class ReviewSession(QObject):
    """Advance one server step at a time and retain uncertain start IDs for retry."""

    changed = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, api: StaffApi, parent: QObject) -> None:
        """Use the staff session for the lifetime of the review widget."""
        super().__init__(parent)
        self.http = ReviewHttp(api, self)
        self.http.received.connect(self._receive)
        self.http.failed.connect(self._failed)
        self.plans: tuple[Plan, ...] = ()
        self.run: Run | None = None
        self.busy = False
        self._target: str | None = None
        self._play_target = False
        self.reset_completed = False
        self._map_hold = QTimer(self)
        self._map_hold.setSingleShot(True)
        self._map_hold.timeout.connect(self._play_prepared_target)
        self._starting: tuple[str, str | None, UUID] | None = None

    def load(self) -> None:
        """Load supported scenarios and resume the latest run for this administrator."""
        if not self.busy:
            self._begin()
            self.http.send('catalog')

    def start(
        self,
        plan: Plan,
        target: str | None = None,
        *,
        play_target: bool = False,
    ) -> None:
        """Create a run, optionally prepare its prefix, and optionally play the target."""
        if self.busy or (target is not None and target not in plan.steps):
            return
        if self._starting is None or self._starting[:2] != (plan.id, target):
            self._starting = (plan.id, target, uuid4())
        self._target = target
        self._play_target = play_target
        self._begin()
        self.http.send(
            'start', '/runs', {'id': str(self._starting[2]), 'plan': plan.id}
        )

    def play_on_map(self, plan: Plan, step: str) -> None:
        """Play the next step inline or replay a separate run for an arbitrary step."""
        if self.run and self.run.plan == plan.id:
            if step in self.run.available:
                self.play(step)
                return
            if self.run.next_step in {'LINK_RESTORED', 'RESUME_APPROVED'}:
                return
        if step in plan.steps:
            self.start(plan, step, play_target=True)

    def play(self, step: str) -> None:
        """Submit an action currently offered by the isolated scenario."""
        if self.busy or self.run is None or step not in self.run.available:
            return
        self._begin()
        self._send_step(step)

    def reset(self, path: str, body: dict[str, Any]) -> None:
        """Cancel prepared playback and request the confirmed review reset."""
        if self.busy and not self._map_hold.isActive():
            return
        self._map_hold.stop()
        self._target = None
        self._play_target = False
        self._starting = None
        self._begin()
        self.http.send('reset', path, body)

    @property
    def can_reset(self) -> bool:
        """Allow reset while idle or during the local map hold before a POST."""
        return not self.busy or self._map_hold.isActive()

    def _begin(self) -> None:
        self.busy = True
        self.changed.emit()

    def _send_step(self, step: str) -> None:
        assert self.run is not None
        self.http.send('step', f'/runs/{self.run.id}/steps/{step}', {})

    def _receive(self, operation: str, payload: dict[str, Any]) -> None:
        try:
            if operation == 'reset':
                self.run = None
                self.reset_completed = True
            elif operation == 'catalog':
                plans = tuple(Plan.parse(p) for p in records(payload, 'plans'))
                latest = payload.get('latest')
                self.run = (
                    Run.parse(object_value(latest)) if latest is not None else None
                )
                self.plans = plans
            else:
                self.run = Run.parse(payload)
                if operation == 'start':
                    self._starting = None
        except (ValueError, TypeError):
            self._failed('SCENARIO_INVALID_RESPONSE')
            return
        next_step = self.run.next_step if self.run else None
        if self._target is not None and next_step and next_step != self._target:
            self.changed.emit()
            self._send_step(next_step)
            return
        if (
            self._play_target
            and self._target is not None
            and self.run is not None
            and self.run.next_step == self._target
        ):
            # Let the local map poll and settle at the predecessor before drawing motion.
            self._map_hold.start(MAP_PREDECESSOR_HOLD_MS)
            self.changed.emit()
            return
        self._target = None
        self._play_target = False
        self.busy = False
        self.changed.emit()

    def _play_prepared_target(self) -> None:
        target, self._target = self._target, None
        self._play_target = False
        if target is not None:
            self._send_step(target)

    def _failed(self, code: str) -> None:
        self._map_hold.stop()
        self._target = None
        self._play_target = False
        self.busy = False
        self.changed.emit()
        self.failed.emit(code)
