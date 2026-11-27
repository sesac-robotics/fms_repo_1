"""Fleet monitoring map and the selected-vehicle data surface."""

from __future__ import annotations

from collections.abc import Callable
from os import getenv

from PyQt6.QtGui import QHideEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import fleet_visibility
from .config import Config, Preferences
from .fleet_map import FleetMap
from .i18n import Text, display_time
from .map_vehicle_selector import MapVehicleSelector
from .models import Snapshot, Vehicle
from .monitor_layout import detail_grid, map_and_cameras
from .preview_panel import PreviewPanel
from .scenario_review_labels import review_stage_text, scenario_card_text
from .vehicle_action_preview import VehicleActionPreview
from .vehicle_details import vehicle_details
from .vision_readings import VisionReading
from .widgets import button, label, panel


class FleetMonitor(QWidget):
    """Show a versioned map, backend snapshots, and one vehicle's details."""

    def __init__(
        self,
        tr: Text,
        config: Config,
        prefs: Preferences,
        selection: Callable[[str], None],
        open_signal: Callable[[str], None] = lambda _: None,
    ) -> None:
        """Build the localized monitoring view from the approved Figma palette."""
        super().__init__()
        self._tr = tr
        self._select = selection
        self._vehicles: tuple[Vehicle, ...] = ()
        self._vision: tuple[VisionReading, ...] = ()
        self._scenario: Vehicle | None = None
        self._review_vehicle = ''
        content = QHBoxLayout(self)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(14)

        body, body_layout = panel()
        body_layout.addWidget(label(tr('map'), 'heading'))
        self._stage = label('', 'heading')
        self._stage.hide()
        body_layout.addWidget(self._stage)
        self._map = FleetMap(tr, config, prefs, open_signal)
        body_layout.addWidget(self._map, 1)
        self._map_selection = MapVehicleSelector(self._choose_vehicle)
        body_layout.addWidget(self._map_selection)

        sidebar = QWidget()
        right = QVBoxLayout(sidebar)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)
        self._previews = PreviewPanel(
            tr,
            self._choose_vehicle,
            test_images=getenv('AMO_FMS_TEST_IMAGES') == '1',
            local_directory=getenv('AMO_FMS_PREVIEW_DIRECTORY'),
        )
        right.addWidget(self._previews, 1)
        self._scenario_card = button('')
        self._scenario_card.setCheckable(True)
        self._scenario_card.clicked.connect(self._choose_scenario)
        self._scenario_card.hide()
        right.addWidget(self._scenario_card)
        self._count = label(tr('fleet_count', count=0), 'secondary')
        right.addWidget(self._count)
        self._recent = label('', 'secondary', wrap=False)
        right.addWidget(self._recent)

        details, detail_layout = panel()
        detail_layout.addWidget(label(tr('selected'), 'heading'))
        self._detail_stage = label('', 'secondary')
        self._detail_stage.hide()
        detail_layout.addWidget(self._detail_stage)
        grid, self._values = detail_grid(tr)
        detail_layout.addLayout(grid)
        self._actions = button(tr('commands'), 'primary')
        self._actions.setEnabled(False)
        self._actions.clicked.connect(self._open_actions)
        detail_layout.addWidget(self._actions)
        self._detail_stack = QStackedWidget()
        self._detail_stack.addWidget(details)
        self._action_preview = VehicleActionPreview(tr)
        self._action_preview.close_requested.connect(self._close_actions)
        self._detail_stack.addWidget(self._action_preview)
        right.addWidget(self._detail_stack)
        content.addWidget(map_and_cameras(body, sidebar))

    def show_snapshot(self, snapshot: Snapshot, selected_id: str) -> None:
        """Update the fleet while preserving the selected vehicle's service ID."""
        self._vision = snapshot.vision
        review = snapshot.review
        current = None if review else fleet_visibility.latest_review_stage(snapshot)
        self._review_vehicle = current.vehicle if snapshot.demo and current else ''
        self._map.set_replay_available(bool(self._review_vehicle))
        self._map.show_board(review, snapshot.signals)
        title = review_stage_text(self._tr, review, current)
        self._stage.setVisible(bool(title))
        self._stage.setText(title)
        self._scenario = fleet_visibility.scenario_vehicle(snapshot)
        self._scenario_card.setText(scenario_card_text(self._tr, self._scenario))
        self._scenario_card.setVisible(self._scenario is not None)
        vehicles = tuple(
            v
            for v in snapshot.vehicles
            if not fleet_visibility.is_scenario_vehicle(v.number)
        )
        if self._vehicles != vehicles:
            self._vehicles = vehicles
            self._map_selection.set_vehicles(vehicles)
        count = len(vehicles) + int(self._scenario is not None)
        self._count.setText(self._tr('fleet_count', count=count))
        recent = snapshot.events[0] if snapshot.events else None
        self._recent.setText(
            f'{display_time(recent.time)} · {recent.vehicle} · {self._tr.status(recent.type)}'
            if recent
            else ''
        )
        self._recent.setVisible(recent is not None)
        self.select(selected_id)

    def select(self, vehicle_id: str) -> None:
        """Select a known vehicle by its server ID, with no fallback assumption."""
        is_scenario = self._scenario is not None and self._scenario.id == vehicle_id
        selected = (
            self._scenario
            if is_scenario
            else next((v for v in self._vehicles if v.id == vehicle_id), None)
        )
        self._scenario_card.setChecked(is_scenario)
        self._map_selection.highlight(vehicle_id)
        self._previews.present(self._vehicles, vehicle_id)
        markers = (
            (self._scenario,)
            if self._scenario is not None
            and self._scenario.number == self._review_vehicle
            else ()
        )
        self._map.show_samples(markers, vehicle_id)
        self._map.highlight_review(is_scenario)
        self._detail_stage.setText(self._stage.text() if is_scenario else '')
        self._detail_stage.setVisible(bool(self._detail_stage.text()))
        self._action_preview.present(None if is_scenario else selected)
        if is_scenario or selected is None:
            self._close_actions()
        if selected is None:
            for field in self._values.values():
                field.setText('—')
                field.setToolTip('')
            self._actions.setEnabled(False)
            return
        for key, value in vehicle_details(
            selected, () if is_scenario else self._vision, self._tr
        ).items():
            self._values[key].setText(value)
            self._values[key].setToolTip(value)
        self._actions.setEnabled(not is_scenario)

    def _open_actions(self) -> None:
        self._detail_stack.setCurrentWidget(self._action_preview)
        self._action_preview.focus_action()

    def _close_actions(self) -> None:
        if self._detail_stack.currentIndex() != 0:
            self._action_preview.clear()
            self._detail_stack.setCurrentIndex(0)

    def hideEvent(self, event: QHideEvent | None) -> None:
        """Dismiss the preview when leaving the monitoring screen."""
        self._close_actions()
        super().hideEvent(event)

    def _choose_scenario(self) -> None:
        if self._scenario is not None:
            self._choose_vehicle(self._scenario.id)

    def _choose_vehicle(self, vehicle_id: str) -> None:
        self.select(vehicle_id)
        self._select(vehicle_id)
