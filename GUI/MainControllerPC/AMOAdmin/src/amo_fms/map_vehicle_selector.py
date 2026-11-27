"""Expose registered vehicle selection in the map area without guessing positions."""

from collections.abc import Callable

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .models import Vehicle


class MapVehicleSelector(QWidget):
    """Bind map-area vehicle buttons to the same server IDs as the fleet list."""

    def __init__(self, select: Callable[[str], None]) -> None:
        """Initialize a compact row of vehicle buttons."""
        super().__init__()
        self._select = select
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._buttons: dict[str, QPushButton] = {}

    def set_vehicles(self, vehicles: tuple[Vehicle, ...]) -> None:
        """Rebuild the row from the registered Pinky vehicles in the snapshot."""
        for button in self._buttons.values():
            self._layout.removeWidget(button)
            button.deleteLater()
        self._buttons.clear()
        for vehicle in vehicles:
            if vehicle.number not in ('PINKY-01', 'PINKY-02', 'PINKY-03', 'PINKY-04'):
                continue
            button = QPushButton(vehicle.number, self)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, key=vehicle.id: self._select(key))
            self._layout.addWidget(button)
            self._buttons[vehicle.id] = button

    def highlight(self, selected: str) -> None:
        """Keep exactly the active vehicle highlighted in the row."""
        for vehicle_id, button in self._buttons.items():
            button.setChecked(vehicle_id == selected)
