"""Present clickable ordered Taxi review stages in the separate Admin desktop."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from .i18n import Text
from .scenario_review_history import ReviewHistory
from .scenario_review_labels import EXPECTED, observed_text, step_title
from .scenario_review_session import ReviewSession
from .scenario_review_view import ReviewView, display_steps, review_choices
from .scenario_review_wire import Plan, Run
from .staff_api import StaffApi


class ScenarioReviewPanel(ReviewView):
    """Show the expected result and actual evidence without simulating client screens locally."""

    replay_requested = pyqtSignal()

    def __init__(self, api: StaffApi, tr: Text, parent: QWidget) -> None:
        """Build an isolated review tab and recover the last committed run."""
        super().__init__(tr, parent)
        self._session = ReviewSession(api, self)
        self._session.changed.connect(self._show)
        self._session.failed.connect(self._show_error)
        self._displayed: tuple[Plan, ...] = ()
        self._notice_text = ''
        self._steps: tuple[str, ...] = ()
        self._records = ReviewHistory(api, tr, self._session, self)
        self._plan.currentIndexChanged.connect(self._plan_changed)
        self._list.currentRowChanged.connect(self._details)
        self._list.itemClicked.connect(lambda _: self._play_clicked_step())
        self._start.clicked.connect(lambda: self._start_run(False))
        self._jump.clicked.connect(lambda: self._start_run(True))
        self._reload.clicked.connect(self._load)
        self._play.clicked.connect(self._play_step)
        self._history.clicked.connect(self._records.list_runs)
        self._reset_current.clicked.connect(self._records.close_current)
        self._reset_history.clicked.connect(self._records.confirm_clear)
        self._records.failed.connect(self._show_error)
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

    def _selected_step(self) -> str | None:
        row = self._list.currentRow()
        return self._steps[row] if 0 <= row < len(self._steps) else None

    def _show(self) -> None:
        if self._session.reset_completed:
            self._session.reset_completed = False
            self._notice_text = self._tr('review_reset_done')
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
        self._render_steps(self._selected_step())

    def _plan_changed(self) -> None:
        self._notice_text = ''
        self._render_steps(None)

    def _render_steps(self, selection: str | None) -> None:
        plan = self._selected_plan()
        run = self._run(plan)
        self._list.blockSignals(True)
        self._list.clear()
        self._steps = display_steps(plan, run)
        if self._steps:
            for index, step in enumerate(self._steps, 1):
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
            self._list.setCurrentRow(
                self._steps.index(selection) if selection in self._steps else 0
            )
        self._list.blockSignals(False)
        self._details()

    def _details(self) -> None:
        tr = self._tr
        plan = self._selected_plan()
        run = self._run(plan)
        step = self._selected_step()
        ready = not self._session.busy
        self._plan.setEnabled(ready)
        self._list.setEnabled(ready)
        self._start.setEnabled(ready and plan is not None)
        self._jump.setEnabled(ready and plan is not None and step in plan.steps)
        self._reload.setEnabled(ready)
        self._evidence_only.setEnabled(ready)
        self._play.setEnabled(
            ready and run is not None and run.next_step == step and step is not None
        )
        self._history.setEnabled(ready)
        self._reset_current.setEnabled(
            self._session.can_reset and self._session.run is not None
        )
        self._reset_history.setEnabled(self._session.can_reset)
        self._show_cases(run)
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
            self.replay_requested.emit()
            self._session.start(plan, self._selected_step() if jump else None)

    def _play_clicked_step(self) -> None:
        plan = self._selected_plan()
        if self._evidence_only.isChecked() or plan is None:
            return
        if step := self._selected_step():
            self._notice_text = ''
            self.replay_requested.emit()
            run = self._run()
            if step in plan.steps or (run and step in run.available):
                self._session.play_on_map(plan, step)

    def _play_step(self) -> None:
        plan = self._selected_plan()
        if plan is not None and (step := self._selected_step()) and self._run(plan):
            self._notice_text = ''
            self.replay_requested.emit()
            self._session.play(step)

    def _show_cases(self, run: Run | None) -> None:
        actions = review_choices(run)
        self.show_cases(actions, not self._session.busy, self._choose_case)

    def _choose_case(self, step: str) -> None:
        self._notice_text = ''
        self.replay_requested.emit()
        self._session.play(step)
        if step in self._steps:
            self._list.setCurrentRow(self._steps.index(step))

    def _show_error(self, code: str) -> None:
        message = self._tr(f'review_error_{code.lower()}')
        self._notice_text = code if message.startswith('review_error_') else message
        self._details()

    def _load(self) -> None:
        self._notice_text = ''
        self._session.load()
