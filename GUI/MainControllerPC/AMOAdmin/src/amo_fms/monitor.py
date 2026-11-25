"""Fleet monitoring map and the selected-vehicle data surface."""

from __future__ import annotations

from collections.abc import Callable

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
from .models import Snapshot, Vehicle
from .scenario_review_labels import latest_review_stage, step_title
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
        content.addWidget(body, 4)

        right = QVBoxLayout()
        right.setSpacing(12)
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
            'dispatch_eligibility',
            'position',
            'reported_yaw',
            'reported_speed',
        )
        for row, key in enumerate(fields):
            name = label(tr(key), 'secondary', wrap=False)
            value = label('—')
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
        current = latest_review_stage(snapshot)
        self._review_vehicle = current.vehicle if snapshot.demo and current else ''
        self._map.set_replay_available(bool(self._review_vehicle))
        self._stage.setVisible(current is not None)
        if current is not None:
            title = step_title(self._tr, current.type.removeprefix('DEMO_REVIEW_'))
            self._stage.setText(
                f'{self._tr("review_tab")} · {current.vehicle} · {title}'
            )
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
        self._list.blockSignals(False)
        markers = tuple(v for v in self._vehicles if v.number == self._review_vehicle)
        self._map.show_samples(markers, vehicle_id)
        if selected is None:
            for field in self._values.values():
                field.setText('—')
            self._actions.setEnabled(False)
            return
        self._values['vehicle_no'].setText(selected.number)
        self._values['status'].setText(self._tr.status(selected.status))
        battery = selected.battery_percent
        self._values['battery'].setText(
            f'{battery:g}%' if battery is not None else self._tr('unknown')
        )
        self._values['connection'].setText(self._tr.status(selected.connection))
        self._values['stop_reason'].setText(self._tr.status(selected.stop_reason))
        eligibility = self._tr('unknown')
        if selected.dispatch_enabled is not None:
            eligibility = self._tr(
                'dispatch_allowed' if selected.dispatch_enabled else 'dispatch_blocked'
            )
        self._values['dispatch_eligibility'].setText(eligibility)
        position = selected.position_m
        self._values['position'].setText(
            f'{position[0]:.3f}, {position[1]:.3f} m'
            if position is not None
            else self._tr('unknown')
        )
        for field, value, unit in (
            ('reported_yaw', selected.yaw_rad, 'rad'),
            ('reported_speed', selected.speed_mps, 'm/s'),
        ):
            self._values[field].setText(
                f'{value:.3f} {unit}' if value is not None else self._tr('unknown')
            )
        self._actions.setEnabled(True)

    def _changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        selected_id = str(current.data(Qt.ItemDataRole.UserRole)) if current else ''
        self.select(selected_id)
        self._select(selected_id)
