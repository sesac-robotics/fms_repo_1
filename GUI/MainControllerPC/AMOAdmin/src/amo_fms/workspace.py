"""Workspace navigation for the localized FMS surfaces."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Preferences
from .i18n import Text
from .models import Operator, Snapshot
from .monitor import FleetMonitor
from .operations_pages import ActionsPage, RecordsPage
from .widgets import brand, button, label

PAGE_KEYS = ('monitor', 'queue', 'events', 'commands')


class Workspace(QWidget):
    """Hold the responsive screen layout and a stable set of operation pages."""

    request_settings = pyqtSignal()
    request_logout = pyqtSignal()
    request_refresh = pyqtSignal()
    vehicle_selected = pyqtSignal(str)
    page_selected = pyqtSignal(str)

    def __init__(
        self,
        tr: Text,
        config: Config,
        prefs: Preferences,
        operator: Operator,
        initial_page: str,
    ) -> None:
        """Construct the live-view shell and preserve navigational state."""
        super().__init__()
        self._tr = tr
        self._nav: dict[str, QPushButton] = {}
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._rail(config, prefs, operator))
        main = QWidget()
        body = QVBoxLayout(main)
        body.setContentsMargins(25, 20, 25, 20)
        body.setSpacing(13)
        body.addLayout(self._top())
        self._caption = label('', 'secondary')
        body.addWidget(self._caption)
        self._status = label(tr('snapshot_wait'), 'secondary')
        body.addWidget(self._status)
        self._stack = QStackedWidget()
        self._monitor = FleetMonitor(
            tr,
            config,
            prefs,
            self.vehicle_selected.emit,
            lambda: self.navigate('commands'),
        )
        self._pages = (
            self._monitor,
            RecordsPage(tr, 'queue'),
            RecordsPage(tr, 'events'),
            ActionsPage(tr, self.vehicle_selected.emit),
        )
        for page in self._pages:
            self._stack.addWidget(page)
        body.addWidget(self._stack, 1)
        outer.addWidget(main, 1)
        self.navigate(initial_page)

    def _rail(self, config: Config, prefs: Preferences, operator: Operator) -> QWidget:
        tr = self._tr
        rail = QWidget()
        rail.setObjectName('rail')
        rail.setMinimumWidth(197)
        rail.setMaximumWidth(229)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(17, 21, 17, 20)
        layout.setSpacing(10)
        layout.addWidget(brand(config, prefs.theme))
        layout.addWidget(label(tr('nav_label'), 'secondary'))
        layout.addSpacing(17)
        for name in PAGE_KEYS:
            item = button(tr(name), 'navigation')
            item.setCheckable(True)
            item.clicked.connect(lambda _checked=False, key=name: self.navigate(key))
            layout.addWidget(item)
            self._nav[name] = item
        layout.addStretch(1)
        settings = button(tr('settings'), 'navigation')
        settings.clicked.connect(self.request_settings)
        layout.addWidget(settings)
        layout.addSpacing(12)
        layout.addWidget(label(operator.name or operator.email, 'heading'))
        layout.addWidget(label(tr.status(operator.role), 'secondary'))
        signout = button(tr('sign_out'), 'navigation')
        signout.clicked.connect(self.request_logout)
        layout.addWidget(signout)
        return rail

    def _top(self) -> QHBoxLayout:
        top = QHBoxLayout()
        self._title: QLabel = label('', 'title')
        top.addWidget(self._title, 1)
        preview = label(self._tr('preview'), 'warning', wrap=False)
        preview.setToolTip(self._tr('preview_explain'))
        preview.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(preview)
        refresh = button(self._tr('refresh'))
        refresh.clicked.connect(self.request_refresh)
        top.addWidget(refresh)
        return top

    def navigate(self, key: str) -> None:
        """Change the displayed page while keeping the data snapshot read-only."""
        page = key if key in PAGE_KEYS else 'monitor'
        self._stack.setCurrentIndex(PAGE_KEYS.index(page))
        self._title.setText(self._tr(page))
        self._caption.setText(
            self._tr('live_caption' if page == 'monitor' else 'preview_explain')
        )
        for name, item in self._nav.items():
            item.setChecked(name == page)
        self.page_selected.emit(page)

    def show_snapshot(self, snapshot: Snapshot, selected: str) -> None:
        """Present one consistent snapshot to all pages."""
        for page in self._pages:
            page.show_snapshot(snapshot, selected)

    def tell(self, text: str) -> None:
        """Display a localized retrieval timestamp or connectivity warning."""
        self._status.setText(text)
