"""Assemble the shared staff workspace for either desktop entry point."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from .comparison_history import HistoryPanel
from .comparison_members import MembersPanel
from .comparison_menus import MenuPanel
from .comparison_operations import OperationTabs
from .comparison_tabs import ComparisonTabs
from .config import Config, Preferences
from .i18n import Text
from .scenario_review_panel import ScenarioReviewPanel
from .staff_api import StaffApi
from .widgets import FitImage


class AdminWorkspace(ComparisonTabs):
    """Share staff tabs while leaving snapshot delivery to the owning window."""

    replay_requested = pyqtSignal()

    def __init__(
        self,
        api: StaffApi,
        role: str,
        config: Config,
        prefs: Preferences,
        open_settings: Callable[[], None],
        parent: QWidget,
    ) -> None:
        """Create the allowed tabs and reuse the server's display metadata."""
        super().__init__(api, role, prefs.language, parent)
        if role == 'ADMIN':
            self.add_menu('members', MembersPanel(api, self), 'Members and roles')
        map_asset = config.asset('legacy_map', prefs.language, prefs.theme)
        self._trips = HistoryPanel(api, 'trip-history', self, asset=str(map_asset))
        self.add_menu('trips', self._trips, 'Trip history')
        self.add_menu('tests', HistoryPanel(api, 'test-history', self), 'Test results')
        tr = Text(prefs.language)
        operations = OperationTabs(tr, open_settings)
        overview = QWidget()
        layout = QHBoxLayout(overview)
        layout.addWidget(operations.overview, 1)
        layout.addWidget(
            FitImage(
                config.asset('map', prefs.language, prefs.theme),
                tr('map_caption'),
                tr('map_missing'),
            ),
            2,
        )
        self.add_menu('overview', overview, 'Overview')
        self.add_menu('logs', operations.logs, 'Operations log')
        self.add_menu('codes', operations.codes, 'Operation codes')
        if role == 'ADMIN':
            menu = MenuPanel(api, self)
            menu.changed.connect(self.load)
            self.add_menu('menu', menu, 'Menu management')
        self.add_menu('settings', operations.settings, 'Settings')
        self.operations = operations
        if role == 'ADMIN' and config.scenario_review:
            review = ScenarioReviewPanel(api, tr, self._review_history, self)
            review.replay_requested.connect(self.replay_requested)
            self.add_menu('scenario-review', review, tr('review_tab'))

    def _review_history(self, request_id: int) -> None:
        self.setCurrentWidget(self._trips)
        self._trips.show_request(request_id)
