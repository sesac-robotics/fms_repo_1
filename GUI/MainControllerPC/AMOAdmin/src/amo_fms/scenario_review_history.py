"""List review-only observations and confirm scoped destructive actions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget

from .i18n import Text
from .models import object_value, records, string_field
from .scenario_review_labels import observed_text, step_title
from .scenario_review_session import ReviewSession
from .scenario_review_wire import ReviewHttp, Run
from .staff_api import StaffApi


class ReviewHistory(QObject):
    """Use review endpoints for history so operation history remains separate."""

    failed = pyqtSignal(str)

    def __init__(
        self, api: StaffApi, tr: Text, session: ReviewSession, parent: QWidget
    ) -> None:
        """Bind history dialogs and resets to this review window."""
        super().__init__(parent)
        self._view = parent
        self._tr = tr
        self._session = session
        self._http = ReviewHttp(api, self)
        self._http.received.connect(self._received)
        self._http.failed.connect(self.failed)

    def list_runs(self) -> None:
        """Fetch the administrator's recent runs, including preserved legacy entries."""
        self._http.send('history', '/history')

    def close_current(self) -> None:
        """Cancel the selected run and retain its committed observations."""
        if self._session.run is not None:
            self._session.reset(f'/runs/{self._session.run.id}/reset', {})

    def confirm_clear(self) -> None:
        """Fetch up-to-date review-only counts before requesting confirmation."""
        self._http.send('counts')

    def _received(self, action: str, data: dict[str, Any]) -> None:
        try:
            if action == 'history':
                self._select_run(records(data, 'runs'))
            elif action == 'counts':
                self._confirm(object_value(data.get('history')))
            else:
                self._show_evidence(Run.parse(data))
        except (TypeError, ValueError):
            self.failed.emit('SCENARIO_INVALID_RESPONSE')

    def _confirm(self, counts: dict[str, Any]) -> None:
        tr = self._tr
        runs, observations = counts.get('runs'), counts.get('observations')
        if type(runs) is not int or type(observations) is not int:
            raise ValueError('Invalid review history counts.')
        if not runs:
            QMessageBox.information(
                self._view, tr('review_history'), tr('review_empty')
            )
            return
        accepted = QMessageBox.question(
            self._view,
            tr('review_reset_history'),
            tr('review_reset_confirm', runs=runs, observations=observations),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if accepted == QMessageBox.StandardButton.Yes:
            self._session.reset('/history/reset', counts)

    def _select_run(self, rows: list[dict[str, Any]]) -> None:
        tr = self._tr
        choices = {}
        for row in rows:
            run_id = UUID(string_field(row, 'id'))
            plan = tr(f'review_plan_{string_field(row, "plan").lower()}')
            state = 'review_archived' if row.get('archived') else 'review_saved'
            if row.get('active'):
                state = 'review_ready'
            choices[f'{plan} · {tr(state)} · {run_id}'] = run_id
        if not choices:
            QMessageBox.information(
                self._view, tr('review_history'), tr('review_empty')
            )
            return
        selection, accepted = QInputDialog.getItem(
            self._view,
            tr('review_history'),
            tr('review_steps'),
            tuple(choices),
            0,
            False,
        )
        if accepted:
            self._http.send('evidence', f'/runs/{choices[selection]}')

    def _show_evidence(self, run: Run) -> None:
        dialog = QMessageBox(self._view)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.setWindowTitle(self._tr('review_history'))
        dialog.setText(f'{run.vehicle_number} · {run.id}')
        dialog.setDetailedText(
            '\n\n'.join(
                f'{step_title(self._tr, step)}\n{observed_text(self._tr, evidence)}'
                for step, evidence in run.completed.items()
            )
            or self._tr('review_empty')
        )
        dialog.exec()
