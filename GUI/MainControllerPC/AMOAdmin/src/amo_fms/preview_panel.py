"""Render four vehicle previews and forward selections without network I/O."""

from collections.abc import Callable

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QGridLayout, QPushButton, QSizePolicy, QWidget

from .i18n import Text
from .models import Vehicle

_NUMBERS = tuple(f'PINKY-{number:02d}' for number in range(1, 5))
_COLORS = ('#234751', '#465573', '#38564e', '#654956')


def _test_image(number: str, index: int) -> QPixmap:
    image = QPixmap(192, 108)
    image.fill(QColor(_COLORS[index]))
    painter = QPainter(image)
    painter.setPen(QColor('#ffffff'))
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, number)
    painter.end()
    return image


class PreviewPanel(QWidget):
    """Display four registered vehicles and an optional synthetic image per slot."""

    def __init__(
        self, tr: Text, select: Callable[[str], None], *, test_images: bool = False
    ) -> None:
        """Create the four slots and connect each to the shared vehicle selection."""
        super().__init__()
        self._tr = tr
        self._select = select
        self._test_images = test_images
        self._selected = ''
        self._vehicles: dict[str, str] = {}
        self._cards: dict[str, QPushButton] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for index, number in enumerate(_NUMBERS):
            card = QPushButton(self)
            card.setCheckable(True)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.clicked.connect(lambda _checked, key=number: self._choose(key))
            if test_images:
                card.setIcon(QIcon(_test_image(number, index)))
                card.setIconSize(QSize(100, 56))
            layout.addWidget(card, index // 2, index % 2)
            self._cards[number] = card
        self._expand = QPushButton(tr('camera_expand'), self)
        self._expand.setCheckable(True)
        self._expand.toggled.connect(self._show_selection)
        layout.addWidget(self._expand, 2, 0, 1, 2)
        self.present((), '')

    def present(self, vehicles: tuple[Vehicle, ...], selected: str) -> None:
        """Associate each registered number with its snapshot ID and highlight it."""
        self._vehicles = {vehicle.number: vehicle.id for vehicle in vehicles}
        self._selected = selected
        for number, card in self._cards.items():
            vehicle_id = self._vehicles.get(number)
            card.setEnabled(vehicle_id is not None)
            card.setChecked(vehicle_id is not None and vehicle_id == selected)
            status = 'camera_test_image' if self._test_images else 'camera_waiting'
            card.setText(f'{number}\n{self._tr(status)}')
        self._expand.setEnabled(selected != '' and selected in self._vehicles.values())
        if not self._expand.isEnabled():
            self._expand.setChecked(False)
        self._show_selection(self._expand.isChecked())

    def _show_selection(self, expanded: bool) -> None:
        self._expand.setText(self._tr('camera_grid' if expanded else 'camera_expand'))
        for number, card in self._cards.items():
            card.setVisible(
                not expanded or self._vehicles.get(number) == self._selected
            )
            card.setIconSize(QSize(160, 90) if expanded else QSize(100, 56))

    def _choose(self, number: str) -> None:
        vehicle_id = self._vehicles.get(number)
        if vehicle_id is not None:
            self._select(vehicle_id)
