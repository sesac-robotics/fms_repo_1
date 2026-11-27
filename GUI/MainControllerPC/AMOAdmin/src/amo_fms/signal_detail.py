"""Per-intersection timing editor: one plan per board, linked on coordinated junctions."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from .i18n import Text
from .signal_commands import SignalCommandSender
from .signal_directions import COORDINATED, Coordination, head_names
from .signal_plan_editor import EAST_GREEN, EAST_YELLOW, PlanEditor
from .signal_readings import SignalReading
from .widgets import button, label, panel


class JunctionDetail(QWidget):
    """Edit one intersection's plans; emits ``closed`` on apply or cancel."""

    closed = pyqtSignal()

    def __init__(
        self,
        tr: Text,
        sender: SignalCommandSender | None,
        report: Callable[[str, str], None],
    ) -> None:
        """``report(junction_key, text)`` receives each command's outcome."""
        super().__init__()
        self._tr = tr
        self._sender = sender
        self._report = report
        self._key = ''
        # Each editor with the boards it sets: one board, or every board of a
        # coordinated junction.
        self._editors: list[tuple[PlanEditor, tuple[str, ...]]] = []
        self._plans: dict[str, tuple[int, ...]] = {}
        self._rule: Coordination | None = None
        card, layout = panel()
        self._title = label('', 'heading')
        layout.addWidget(self._title)
        self._list = QVBoxLayout()
        self._list.setSpacing(14)
        layout.addLayout(self._list)
        self._notice = label('', 'warning')
        layout.addWidget(self._notice)
        actions = QHBoxLayout()
        self.apply = button(tr('signal_apply'), 'primary')
        self.apply.clicked.connect(self._apply)
        self.cancel = button(tr('signal_cancel'))
        self.cancel.clicked.connect(self.closed.emit)
        actions.addWidget(self.apply)
        actions.addWidget(self.cancel)
        actions.addStretch(1)
        layout.addLayout(actions)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        outer.addStretch(1)

    def open(self, key: str, readings: list[SignalReading]) -> None:
        """Show the editors for one intersection, filled with the reported plans."""
        self._key = key
        while self._list.count():
            item = self._list.takeAt(0)
            if item is not None and (widget := item.widget()) is not None:
                widget.deleteLater()
        tr = self._tr
        self._title.setText(tr('signal_detail_title', name=tr(key)))
        self._plans = {reading.signal_id: reading.plan_ms for reading in readings}
        self._rule = COORDINATED.get(key) if len(readings) > 1 else None
        self._editors = []
        for reading in readings:
            names = head_names(tr, reading.signal_id)
            editor = PlanEditor(tr, reading.signal_id, names)
            editor.show_plan(reading.plan_ms)
            editor.set_writable(self._sender is not None)
            self._editors.append((editor, (reading.signal_id,)))
            self._list.addWidget(editor)
        if self._rule is not None:
            # Linked fields are one timing for the junction: editing one on any
            # board moves it on the others (QDoubleSpinBox only signals real
            # changes, so the mirror stops). Other fields stay per board.
            for first, _ids in self._editors:
                for second, _other in self._editors:
                    if first is not second:
                        first.link(second, self._rule.linked)
            ids = ' · '.join(self._plans)
            note = label(tr(self._rule.note, ids=ids), 'secondary')
            self._list.insertWidget(0, note)
        self.apply.setEnabled(self._sender is not None)
        self._notice.setText('' if self._sender else tr('signal_read_only'))

    def show_readings(self, readings: tuple[SignalReading, ...]) -> None:
        """Follow reported plans; fields the operator edited keep their values."""
        for reading in readings:
            if reading.signal_id in self._plans:
                self._plans[reading.signal_id] = reading.plan_ms
        for editor, ids in self._editors:
            editor.show_plan(self._plans[ids[0]])

    def _partner_ms(self, editor: PlanEditor) -> int:
        """With separate east turns, the other boards' east green plus yellow."""
        if self._rule is None or not self._rule.east_turns:
            return 0
        return sum(
            other.millis()[EAST_GREEN] + other.millis()[EAST_YELLOW]
            for other, _ids in self._editors
            if other is not editor
        )

    def _apply(self) -> None:
        commands: list[tuple[str, str]] = []
        for editor, ids in self._editors:
            partner = self._partner_ms(editor)
            if (*editor.millis(), partner) == self._plans.get(ids[0]):
                continue
            command = editor.command(partner)
            if command is None:
                self._notice.setText(self._tr('signal_plan_invalid'))
                return
            commands.append((ids[0], command))
        if self._sender is None:
            return
        key, tr = self._key, self._tr
        for signal_id, command in commands:
            self._sender.send(
                signal_id,
                command,
                lambda result, sid=signal_id: self._report(
                    key, f'{sid} · {tr(result)}'
                ),
            )
        self._report(key, tr('signal_sending') if commands else '')
        self.closed.emit()
