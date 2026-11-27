"""Overview card for one intersection: lamps, server reception and next change."""

from __future__ import annotations

import time
from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from .i18n import Text
from .signal_directions import head_names, is_pedestrian
from .signal_head import ORDER, WALK, SignalHead
from .signal_readings import SignalReading
from .widgets import button, label, panel

_STALE_S = 5.0


class SignalBlock(QWidget):
    """One board: its two heads, whether reports arrive, and the next change."""

    def __init__(self, tr: Text, signal_id: str) -> None:
        """Label the heads with the board's directions."""
        super().__init__()
        self._tr = tr
        self._reading: SignalReading | None = None
        self._seen = 0.0
        self._changed = 0.0
        names = head_names(tr, signal_id)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(label(signal_id, 'heading', wrap=False))
        heads = QGridLayout()
        heads.setHorizontalSpacing(14)
        self.heads: list[SignalHead] = []
        lamps = (WALK if is_pedestrian(signal_id) else ORDER, ORDER)
        for column, (key, kind) in enumerate(
            zip(('signal_north', 'signal_east'), lamps, strict=True)
        ):
            head = SignalHead(kind)
            self.heads.append(head)
            heads.addWidget(head, 0, column, Qt.AlignmentFlag.AlignHCenter)
            caption = label(tr(key, **names), 'secondary', wrap=False)
            heads.addWidget(caption, 1, column, Qt.AlignmentFlag.AlignHCenter)
        heads.setRowMinimumHeight(0, self.heads[1].height())
        layout.addLayout(heads)
        self.live = label(tr('signal_live'), 'secondary', wrap=False)
        self.stale = label('', 'warning', wrap=False)
        self.next = label('—', wrap=False)
        for widget in (self.live, self.stale, self.next):
            layout.addWidget(widget)

    def show_reading(self, reading: SignalReading) -> None:
        """Light the lamps and restart the countdown from the new report."""
        now = time.monotonic()
        if self._reading is None or self._reading.received_at != reading.received_at:
            self._changed = now
        self._reading, self._seen = reading, now
        for head, lamp in zip(self.heads, reading.lamps(), strict=True):
            head.set_lit(lamp)
        self.tick()

    def tick(self) -> None:
        """Count down locally between snapshots and flag a silent board."""
        reading = self._reading
        if reading is None:
            return
        now = time.monotonic()
        if reading.mode == 'HOLD' and reading.remaining_ms == 0:
            self.next.setText(self._tr('signal_holding'))
        else:
            left = max(0.0, reading.remaining_ms / 1000 - (now - self._seen))
            self.next.setText(self._tr('signal_next', seconds=f'{left:.1f}'))
        quiet = now - self._changed
        stale = quiet > _STALE_S
        self.live.setVisible(not stale)
        self.stale.setVisible(stale)
        self.stale.setText(
            self._tr('signal_stale', seconds=int(quiet)) if stale else ''
        )


class JunctionCard(QWidget):
    """One intersection's boards side by side, with a button to its details."""

    def __init__(self, tr: Text, key: str, open_detail: Callable[[str], None]) -> None:
        """``open_detail(key)`` runs when the details button is pressed."""
        super().__init__()
        self._tr = tr
        self.blocks: dict[str, SignalBlock] = {}
        card, layout = panel()
        header = QHBoxLayout()
        header.addWidget(label(tr(key), 'heading', wrap=False))
        header.addStretch(1)
        self.detail = button(tr('signal_detail'))
        self.detail.clicked.connect(lambda: open_detail(key))
        header.addWidget(self.detail)
        layout.addLayout(header)
        self._row = QHBoxLayout()
        self._row.setSpacing(40)
        self._row.addStretch(1)
        layout.addLayout(self._row)
        self.mismatch = label(tr('signal_plan_mismatch'), 'warning')
        self.mismatch.setVisible(False)
        layout.addWidget(self.mismatch)
        self.status = label('', 'secondary')
        self.status.setVisible(False)
        layout.addWidget(self.status)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    def show_readings(self, readings: list[SignalReading]) -> None:
        """Add a block per new board and update the rest."""
        for reading in readings:
            block = self.blocks.get(reading.signal_id)
            if block is None:
                block = SignalBlock(self._tr, reading.signal_id)
                self.blocks[reading.signal_id] = block
                self._row.insertWidget(self._row.count() - 1, block)
            block.show_reading(reading)

    def tell(self, text: str) -> None:
        """Show the outcome of the last apply under the boards."""
        self.status.setText(text)
        self.status.setVisible(bool(text))

    def tick(self) -> None:
        """Advance every board's countdown."""
        for block in self.blocks.values():
            block.tick()
