"""Assemble the shared staff workspace for either desktop entry point."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QWidget

from .comparison_history import HistoryPanel
from .comparison_members import MembersPanel
from .comparison_menus import MenuPanel
from .comparison_operations import OperationTabs
from .comparison_tabs import ComparisonTabs
from .config import Config, Preferences
from .i18n import Text
from .scenario_review_panel import ScenarioReviewPanel
from .staff_api import StaffApi


class AdminWorkspace(ComparisonTabs):
    """Share staff tabs while leaving snapshot delivery to the owning window."""

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
        map_asset = config.asset('map', prefs.language, prefs.theme)
        self._trips = HistoryPanel(api, 'trip-history', self, asset=str(map_asset))
        self.add_menu('trips', self._trips, 'Trip history')
        self.add_menu('tests', HistoryPanel(api, 'test-history', self), 'Test results')
        operations = OperationTabs(Text(prefs.language), open_settings)
        self.add_menu('overview', operations.overview, 'Overview')
        self.add_menu('logs', operations.logs, 'Operations log')
        self.add_menu('codes', operations.codes, 'Operation codes')
        if role == 'ADMIN':
            menu = MenuPanel(api, self)
            menu.changed.connect(self.load)
            self.add_menu('menu', menu, 'Menu management')
        self.add_menu('settings', operations.settings, 'Settings')
        self.operations = operations
        if role == 'ADMIN' and config.scenario_review:
            tr = Text(prefs.language)
            review = ScenarioReviewPanel(api, tr, self._review_history, self)
            self.add_menu('scenario-review', review, tr('review_tab'))

    def _review_history(self, request_id: int) -> None:
        self.setCurrentWidget(self._trips)
        self._trips.show_request(request_id)
