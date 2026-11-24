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
        self._manual_target = False
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
        manual: bool = False,
    ) -> None:
        """Create a run, optionally prepare its prefix, and optionally play the target."""
        if self.busy or (target is not None and target not in plan.steps):
            return
        if self._starting is None or self._starting[:2] != (plan.id, target):
            self._starting = (plan.id, target, uuid4())
        self._target = target
        self._play_target = play_target
        self._manual_target = manual
        self._begin()
        self.http.send(
            'start', '/runs', {'id': str(self._starting[2]), 'plan': plan.id}
        )

    def play_on_map(self, plan: Plan, step: str, *, manual: bool = False) -> None:
        """Play the next step inline or replay a separate run for an arbitrary step."""
        if self.run and self.run.plan == plan.id and self.run.next_step == step:
            self.play(step, manual=manual)
        else:
            self.start(plan, step, play_target=True, manual=manual)

    def play(self, step: str, *, manual: bool = False) -> None:
        """Submit only the current server checkpoint and optionally verify Android input."""
        if self.busy or self.run is None or self.run.next_step != step:
            return
        self._begin()
        self._send_step(step, manual)

    def _begin(self) -> None:
        self.busy = True
        self.changed.emit()

    def _send_step(self, step: str, manual: bool) -> None:
        assert self.run is not None
        self.http.send('step', f'/runs/{self.run.id}/steps/{step}', {'manual': manual})

    def _receive(self, operation: str, payload: dict[str, Any]) -> None:
        try:
            if operation == 'catalog':
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
        if (
            self._target is not None
            and self.run is not None
            and self.run.next_step not in {None, self._target}
        ):
            self.changed.emit()
            self._send_step(self.run.next_step, False)
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
            self._send_step(target, self._manual_target)

    def _failed(self, code: str) -> None:
        self._map_hold.stop()
        self._target = None
        self._play_target = False
        self.busy = False
        self.changed.emit()
        self.failed.emit(code)
