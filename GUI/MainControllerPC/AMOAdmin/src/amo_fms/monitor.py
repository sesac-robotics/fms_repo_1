"""Fleet monitoring map and the selected-vehicle data surface."""

from __future__ import annotations

from collections.abc import Callable
from os import getenv

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Preferences
from .fleet_map import FleetMap
from .i18n import Text, display_time
from .map_vehicle_selector import MapVehicleSelector
from .models import Snapshot, Vehicle
from .preview_panel import PreviewPanel
from .scenario_review_labels import latest_review_stage, review_stage_text
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
        open_actions: Callable[[], None],
    ) -> None:
        """Build the localized monitoring view from the approved Figma palette."""
        super().__init__()
        self._tr = tr
        self._select = selection
        self._vehicles: tuple[Vehicle, ...] = ()
        self._vision: tuple[VisionReading, ...] = ()
        self._selected_id = ''
        self._review_vehicle = ''
        content = QHBoxLayout(self)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(14)

        body, body_layout = panel()
        body_layout.addWidget(label(tr('map'), 'heading'))
        self._stage = label('', 'heading')
        self._stage.hide()
        body_layout.addWidget(self._stage)
        self._map = FleetMap(tr, config, prefs)
        body_layout.addWidget(self._map, 1)
        self._map_selection = MapVehicleSelector(self._choose_vehicle)
        body_layout.addWidget(self._map_selection)
        content.addWidget(body, 4)

        right = QVBoxLayout()
        right.setSpacing(12)
        self._previews = PreviewPanel(
            tr, self._choose_vehicle, test_images=getenv('AMO_FMS_TEST_IMAGES') == '1'
        )
        right.addWidget(self._previews)
        fleet, fleet_layout = panel()
        fleet_layout.addWidget(label(tr('fleet'), 'heading'))
        self._count = label(tr('fleet_count', count=0), 'secondary')
        fleet_layout.addWidget(self._count)
        self._list = QListWidget()
        self._list.setAccessibleName(tr('fleet'))
        self._list.setAlternatingRowColors(True)
        self._list.currentItemChanged.connect(self._changed)
        fleet_layout.addWidget(self._list, 1)
        fleet_layout.addWidget(label(tr('latest_event'), 'heading'))
        self._recent = label(tr('empty'), 'secondary')
        fleet_layout.addWidget(self._recent)
        right.addWidget(fleet, 3)

        details, detail_layout = panel()
        detail_layout.addWidget(label(tr('selected'), 'heading'))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(9)
        self._values: dict[str, QLabel] = {}
        fields = (
            'vehicle_no',
            'status',
            'battery',
            'connection',
            'stop_reason',
            'vision_reading',
            'dispatch_setting',
            'dispatch_eligibility',
            'observation_received_at',
            'position',
            'reported_yaw',
            'reported_speed',
        )
        for row, key in enumerate(fields):
            name = label(tr(key), 'secondary', wrap=False)
            value = label('—')
            value.setTextFormat(Qt.TextFormat.PlainText)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            self._values[key] = value
        grid.setColumnMinimumWidth(1, 104)
        grid.setColumnStretch(1, 1)
        detail_layout.addLayout(grid)
        self._actions = button(tr('commands'), 'primary')
        self._actions.setEnabled(False)
        self._actions.clicked.connect(open_actions)
        detail_layout.addWidget(self._actions)
        right.addWidget(details, 2)
        content.addLayout(right, 2)

    def show_snapshot(self, snapshot: Snapshot, selected_id: str) -> None:
        """Update the fleet while preserving the selected vehicle's service ID."""
        self._vision = snapshot.vision
        review = snapshot.review
        current = None if review else latest_review_stage(snapshot)
        self._review_vehicle = current.vehicle if snapshot.demo and current else ''
        self._map.set_replay_available(bool(self._review_vehicle))
        self._map.show_review(review)
        title = review_stage_text(self._tr, review, current)
        self._stage.setVisible(bool(title))
        self._stage.setText(title)
        if snapshot.events:
            event = snapshot.events[0]
            parts = (
                display_time(event.time),
                event.vehicle,
                self._tr.status(event.type),
            )
            self._recent.setText(' · '.join(part for part in parts if part))
        else:
            self._recent.setText(self._tr('empty'))
        if self._vehicles != snapshot.vehicles:
            self._vehicles = snapshot.vehicles
            self._map_selection.set_vehicles(self._vehicles)
            self._list.blockSignals(True)
            self._list.clear()
            for vehicle in self._vehicles:
                item = QListWidgetItem(
                    f'{vehicle.number}  ·  {self._tr.status(vehicle.status)}'
                )
                item.setData(Qt.ItemDataRole.UserRole, vehicle.id)
                self._list.addItem(item)
            self._list.blockSignals(False)
            self._count.setText(self._tr('fleet_count', count=len(self._vehicles)))
        self.select(selected_id)

    def select(self, vehicle_id: str) -> None:
        """Select a known vehicle by its server ID, with no fallback assumption."""
        self._selected_id = vehicle_id
        selected = next((v for v in self._vehicles if v.id == vehicle_id), None)
        row = next((i for i, v in enumerate(self._vehicles) if v.id == vehicle_id), -1)
        self._list.blockSignals(True)
        self._list.setCurrentRow(row)
        self._map_selection.highlight(vehicle_id)
        self._previews.present(self._vehicles, vehicle_id)
        self._list.blockSignals(False)
        markers = tuple(v for v in self._vehicles if v.number == self._review_vehicle)
        self._map.show_samples(markers, vehicle_id)
        if selected is None:
            for field in self._values.values():
                field.setText('—')
            self._actions.setEnabled(False)
            return
        for key, value in vehicle_details(selected, self._vision, self._tr).items():
            self._values[key].setText(value)
        self._actions.setEnabled(True)

    def _changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        selected_id = str(current.data(Qt.ItemDataRole.UserRole)) if current else ''
        self._choose_vehicle(selected_id)

    def _choose_vehicle(self, vehicle_id: str) -> None:
        self.select(vehicle_id)
        self._select(vehicle_id)
