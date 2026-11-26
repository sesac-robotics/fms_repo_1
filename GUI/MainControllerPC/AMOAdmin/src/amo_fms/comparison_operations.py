"""Small read-only administrative tabs backed by the existing fleet snapshot."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from .i18n import Text
from .models import Snapshot


class OperationTabs:
    """Present overview, logs, reference codes and existing desktop preferences."""

    def __init__(self, tr: Text, open_settings: Callable[[], None]) -> None:
        """Create the four views without issuing additional polling requests."""
        self._tr = tr
        self.overview = QListWidget()
        self.logs = QListWidget()
        self.codes = QListWidget()
        self.codes.addItems(
            [f'{code} · {tr(code)}' for code in ('S1', 'S2', 'S3', 'S4')]
        )
        self.settings = QWidget()
        layout = QVBoxLayout(self.settings)
        layout.addWidget(QLabel(tr('settings')))
        edit = QPushButton(tr('settings'))
        edit.clicked.connect(open_settings)
        layout.addWidget(edit)
        layout.addStretch()

    def present(self, snapshot: Snapshot) -> None:
        """Use only the bounded snapshot already fetched for the fleet monitor."""
        self.overview.clear()
        self.overview.addItems(
            [f'{v.number} · {self._tr.status(v.status)}' for v in snapshot.vehicles]
            + [f'#{r.id} · {r.pickup} → {r.destination}' for r in snapshot.requests]
            + [v.admin_summary(self._tr) for v in snapshot.vision]
        )
        self.logs.clear()
        self.logs.addItems(
            [
                f'{e.time} · {e.vehicle} · {self._tr.status(e.type)} · {e.detail}'
                for e in snapshot.events
            ]
        )
