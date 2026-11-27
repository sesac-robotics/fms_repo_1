"""FMS signals page: one card per intersection, with a timing editor behind each."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from .i18n import Text
from .models import Snapshot
from .signal_commands import SignalCommandSender
from .signal_detail import JunctionDetail
from .signal_directions import COORDINATED, JUNCTIONS, OTHER_JUNCTION, junction_key
from .signal_junction_card import JunctionCard
from .signal_plan_editor import junction_agrees
from .signal_readings import SignalReading
from .widgets import label


class SignalsPage(QWidget):
    """Overview of the intersections; each card's details button opens its timing editor."""

    def __init__(
        self,
        tr: Text,
        refresh: Callable[[], None],
        sender: SignalCommandSender | None = None,
    ) -> None:
        """Poll through ``refresh``; send plan changes through ``sender`` if given."""
        super().__init__()
        self._readings: dict[str, SignalReading] = {}
        overview = QWidget()
        listing = QVBoxLayout(overview)
        listing.setContentsMargins(0, 0, 0, 0)
        listing.setSpacing(12)
        self._empty = label(tr('signal_none'), 'secondary')
        listing.addWidget(self._empty)
        self.cards: dict[str, JunctionCard] = {}
        for key in (*(key for key, _members in JUNCTIONS), OTHER_JUNCTION):
            card = JunctionCard(tr, key, self._open)
            card.setVisible(False)
            self.cards[key] = card
            listing.addWidget(card)
        listing.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet('QScrollArea { background: transparent; }')
        scroll.viewport().setAutoFillBackground(False)  # type: ignore[union-attr]
        overview.setAutoFillBackground(False)
        scroll.setWidget(overview)
        self.detail = JunctionDetail(tr, sender, self._tell)
        self.stack = QStackedWidget()
        self.stack.addWidget(scroll)
        self.stack.addWidget(self.detail)
        self.detail.closed.connect(lambda: self.stack.setCurrentIndex(0))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(refresh)
        self._clock = QTimer(self)
        self._clock.setInterval(200)
        self._clock.timeout.connect(self._tick)

    def show_snapshot(self, snapshot: Snapshot, _selected_id: str) -> None:
        """Route each board's report to its intersection card and the editor."""
        for reading in snapshot.signals:
            self._readings[reading.signal_id] = reading
        for key, card in self.cards.items():
            members = self._members(key)
            card.setVisible(bool(members))
            card.show_readings(members)
            # Coordinated boards must fit one cycle, or their phases drift apart.
            plans = [reading.plan_ms for reading in members]
            rule = COORDINATED.get(key)
            card.mismatch.setVisible(
                rule is not None
                and not junction_agrees(plans, rule.linked, rule.east_turns)
            )
        self._empty.setVisible(not self._readings)
        self.detail.show_readings(snapshot.signals)

    def showEvent(self, event: QShowEvent | None) -> None:
        self._poll.start()
        self._clock.start()
        super().showEvent(event)

    def hideEvent(self, event: object) -> None:
        self._poll.stop()
        self._clock.stop()
        self.stack.setCurrentIndex(0)
        super().hideEvent(event)  # type: ignore[arg-type]

    def _members(self, key: str) -> list[SignalReading]:
        return sorted(
            (r for r in self._readings.values() if junction_key(r.signal_id) == key),
            key=lambda reading: reading.signal_id,
        )

    def _open(self, key: str) -> None:
        self.detail.open(key, self._members(key))
        self.stack.setCurrentIndex(1)

    def _tell(self, key: str, text: str) -> None:
        self.cards[key].tell(text)

    def _tick(self) -> None:
        for card in self.cards.values():
            card.tick()
