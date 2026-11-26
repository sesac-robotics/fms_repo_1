"""Read-only FMS page that draws each SignalKit traffic light and its latest report."""

from __future__ import annotations

import time
from collections.abc import Callable

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QShowEvent
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .i18n import Text, display_time
from .models import Snapshot
from .signal_readings import SignalReading
from .widgets import label, panel

_LIT = {'R': '#e5484d', 'Y': '#f5b400', 'G': '#2fbf71'}
_OFF = '#3a3f45'
_STALE_S = 5.0
_FIELDS = ('signal_phase', 'signal_remaining', 'signal_mode', 'signal_plan')
_FIELDS += ('signal_last_command', 'signal_received')


class SignalHead(QWidget):
    """Paint one vertical red, yellow and green head with a single lit lamp."""

    def __init__(self) -> None:
        super().__init__()
        self._lit = 'R'
        self.setFixedSize(64, 172)

    def set_lit(self, lamp: str) -> None:
        if lamp != self._lit:
            self._lit = lamp
            self.update()

    def paintEvent(self, _event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#1f2328'))
        painter.drawRoundedRect(QRectF(0, 0, 64, 172), 14, 14)
        for row, lamp in enumerate('RYG'):
            painter.setBrush(QColor(_LIT[lamp] if lamp == self._lit else _OFF))
            painter.drawEllipse(QRectF(10, 10 + row * 52, 44, 44))
        painter.end()


class SignalCard(QWidget):
    """One signal: north and east heads beside its reported values."""

    def __init__(self, tr: Text) -> None:
        super().__init__()
        self._tr = tr
        self._reading: SignalReading | None = None
        self._seen = 0.0
        self._changed = 0.0
        card, layout = panel()
        self._title = label('', 'heading')
        layout.addWidget(self._title)
        row = QHBoxLayout()
        row.setSpacing(18)
        self._heads: list[SignalHead] = []
        for key in ('signal_north', 'signal_east'):
            column = QVBoxLayout()
            head = SignalHead()
            self._heads.append(head)
            column.addWidget(head, 0, Qt.AlignmentFlag.AlignHCenter)
            caption = label(tr(key), 'secondary', wrap=False)
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(caption)
            row.addLayout(column)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)
        self._values: dict[str, QLabel] = {}
        for index, key in enumerate(_FIELDS):
            grid.addWidget(label(tr(key), 'secondary', wrap=False), index, 0)
            self._values[key] = label('—')
            grid.addWidget(self._values[key], index, 1)
        grid.setColumnStretch(1, 1)
        row.addLayout(grid, 1)
        layout.addLayout(row)
        self._stale = label('', 'warning')
        layout.addWidget(self._stale)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    def show_reading(self, reading: SignalReading) -> None:
        now = time.monotonic()
        previous = self._reading
        if previous is None or previous.received_at != reading.received_at:
            self._changed = now
        self._reading, self._seen = reading, now
        tr = self._tr
        north, east = reading.lamps()
        self._heads[0].set_lit(north)
        self._heads[1].set_lit(east)
        self._title.setText(reading.signal_id)
        self._values['signal_phase'].setText(tr(f'phase_{reading.phase}'))
        mode = tr(f'signal_mode_{reading.mode}')
        if reading.hold_target:
            mode += f' · {tr(f"phase_{reading.hold_target}")}'
        self._values['signal_mode'].setText(mode)
        plan = reading.plan_text()
        if reading.plan_pending:
            plan += f' ({tr("signal_pending")})'
        self._values['signal_plan'].setText(plan)
        command = reading.last_command or '—'
        self._values['signal_last_command'].setText(
            f'{command} · {tr.status(reading.command_result)}'
        )
        self._values['signal_received'].setText(display_time(reading.received_at))
        self.tick()

    def tick(self) -> None:
        """Count the remaining time down locally between snapshots."""
        reading = self._reading
        if reading is None:
            return
        now = time.monotonic()
        if reading.mode == 'HOLD' and reading.remaining_ms == 0:
            text = self._tr('signal_holding')
        else:
            left = max(0.0, reading.remaining_ms / 1000 - (now - self._seen))
            text = f'{left:.1f}s'
        self._values['signal_remaining'].setText(text)
        quiet = now - self._changed
        self._stale.setText(
            self._tr('signal_stale', seconds=int(quiet)) if quiet > _STALE_S else ''
        )


class SignalsPage(QWidget):
    """List every reporting signal; refresh every second while the page is shown."""

    def __init__(self, tr: Text, refresh: Callable[[], None]) -> None:
        super().__init__()
        self._tr = tr
        self._cards: dict[str, SignalCard] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)
        self._empty = label(tr('signal_none'), 'secondary')
        self._layout.addWidget(self._empty)
        self._layout.addStretch(1)
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(refresh)
        self._clock = QTimer(self)
        self._clock.setInterval(200)
        self._clock.timeout.connect(self._tick)

    def show_snapshot(self, snapshot: Snapshot, _selected_id: str) -> None:
        """Add a card for each new signal and update the existing ones."""
        for reading in snapshot.signals:
            card = self._cards.get(reading.signal_id)
            if card is None:
                card = SignalCard(self._tr)
                self._cards[reading.signal_id] = card
                self._layout.insertWidget(self._layout.count() - 1, card)
            card.show_reading(reading)
        self._empty.setVisible(not self._cards)

    def showEvent(self, event: QShowEvent | None) -> None:
        self._poll.start()
        self._clock.start()
        super().showEvent(event)

    def hideEvent(self, event: object) -> None:
        self._poll.stop()
        self._clock.stop()
        super().hideEvent(event)  # type: ignore[arg-type]

    def _tick(self) -> None:
        for card in self._cards.values():
            card.tick()
