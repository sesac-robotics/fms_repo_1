"""Present clickable ordered Taxi review stages in the separate Admin desktop."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from .i18n import Text
from .scenario_review_labels import EXPECTED, observed_text, step_title
from .scenario_review_session import ReviewSession
from .scenario_review_view import ReviewView
from .scenario_review_wire import Plan, Run
from .staff_api import StaffApi


class ScenarioReviewPanel(ReviewView):
    """Show the expected result and actual evidence without simulating client screens locally."""

    replay_requested = pyqtSignal()

    def __init__(
        self, api: StaffApi, tr: Text, open_ride: Callable[[int], None], parent: QWidget
    ) -> None:
        """Build an isolated review tab and recover the last committed run."""
        super().__init__(tr, parent)
        self._open_ride = open_ride
        self._session = ReviewSession(api, self)
        self._session.changed.connect(self._show)
        self._session.failed.connect(self._show_error)
        self._displayed: tuple[Plan, ...] = ()
        self._notice_text = ''
        self._plan.currentIndexChanged.connect(self._plan_changed)
        self._list.currentRowChanged.connect(self._details)
        self._list.itemClicked.connect(lambda _: self._play_clicked_step())
        self._start.clicked.connect(lambda: self._start_run(False))
        self._jump.clicked.connect(lambda: self._start_run(True))
        self._reload.clicked.connect(self._load)
        self._play.clicked.connect(self._play_step)
        self._history.clicked.connect(self._history_clicked)
        self._load()

    def _selected_plan(self) -> Plan | None:
        index = self._plan.currentIndex()
        return self._displayed[index] if 0 <= index < len(self._displayed) else None

    def _run(self, plan: Plan | None = None) -> Run | None:
        plan = plan or self._selected_plan()
        run = self._session.run
        return (
            run
            if run is not None and plan is not None and run.plan == plan.id
            else None
        )

    def _selected_step(self, plan: Plan | None) -> str | None:
        row = self._list.currentRow()
        return (
            plan.steps[row] if plan is not None and 0 <= row < len(plan.steps) else None
        )

    def _show(self) -> None:
        if self._displayed != self._session.plans:
            self._displayed = self._session.plans
            self._plan.blockSignals(True)
            self._plan.clear()
            for plan in self._displayed:
                self._plan.addItem(self._tr(f'review_plan_{plan.id.lower()}'))
            if self._session.run is not None:
                for index, plan in enumerate(self._displayed):
                    if plan.id == self._session.run.plan:
                        self._plan.setCurrentIndex(index)
                        break
            self._plan.blockSignals(False)
        self._render_steps(self._list.currentRow())

    def _plan_changed(self) -> None:
        self._notice_text = ''
        self._render_steps(0)

    def _render_steps(self, selection: int) -> None:
        plan = self._selected_plan()
        run = self._run(plan)
        self._list.blockSignals(True)
        self._list.clear()
        if plan is not None:
            for index, step in enumerate(plan.steps, 1):
                mark = (
                    '✓'
                    if run and step in run.completed
                    else '▶'
                    if run and step == run.next_step
                    else '·'
                )
                sd = EXPECTED.get(step, ('—', ''))[0]
                self._list.addItem(
                    f'{mark} {index:02d}  {sd}  {step_title(self._tr, step)}'
                )
            self._list.setCurrentRow(max(0, min(selection, len(plan.steps) - 1)))
        self._list.blockSignals(False)
        self._details()

    def _details(self) -> None:
        tr = self._tr
        plan = self._selected_plan()
        run = self._run(plan)
        step = self._selected_step(plan)
        ready = not self._session.busy
        self._plan.setEnabled(ready)
        self._list.setEnabled(ready)
        self._start.setEnabled(ready and plan is not None)
        self._jump.setEnabled(ready and step is not None)
        self._reload.setEnabled(ready)
        self._manual.setEnabled(ready)
        self._evidence_only.setEnabled(ready)
        self._play.setEnabled(
            ready and run is not None and run.next_step == step and step is not None
        )
        self._history.setEnabled(
            ready and run is not None and run.request_id is not None
        )
        self._summary.setText(
            tr(
                'review_run',
                id=str(run.id),
                vehicle=run.vehicle_number,
                request=run.request_id or '—',
            )
            if run
            else tr('review_scope')
        )
        evidence = (
            run.completed.get(step) if run is not None and step is not None else None
        )
        expected = tr(f'review_expect_{step.lower()}') if step else ''
        screens = EXPECTED.get(step, ('', ''))[1] if step else ''
        self._expected.setText(
            tr('review_expected', value=expected, screens=screens) if expected else ''
        )
        self._observed.setPlainText(
            observed_text(tr, evidence) if evidence else tr('review_pending')
        )
        self._notice.setText(tr('working') if self._session.busy else self._notice_text)

    def _start_run(self, jump: bool) -> None:
        if plan := self._selected_plan():
            self._notice_text = ''
            self._session.start(plan, self._selected_step(plan) if jump else None)

    def _play_clicked_step(self) -> None:
        plan = self._selected_plan()
        if self._evidence_only.isChecked() or plan is None:
            return
        if step := self._selected_step(plan):
            self._notice_text = ''
            self.replay_requested.emit()
            self._session.play_on_map(
                plan,
                step,
                manual=self._manual.isChecked() and step in plan.manual_steps,
            )

    def _play_step(self) -> None:
        plan = self._selected_plan()
        if plan is not None and (step := self._selected_step(plan)) and self._run(plan):
            self._notice_text = ''
            self.replay_requested.emit()
            self._session.play(
                step, manual=self._manual.isChecked() and step in plan.manual_steps
            )

    def _show_error(self, code: str) -> None:
        message = self._tr(f'review_error_{code.lower()}')
        self._notice_text = code if message.startswith('review_error_') else message
        self._details()

    def _load(self) -> None:
        self._notice_text = ''
        self._session.load()

    def _history_clicked(self) -> None:
        if (run := self._run()) is not None and run.request_id is not None:
            self._open_ride(run.request_id)
