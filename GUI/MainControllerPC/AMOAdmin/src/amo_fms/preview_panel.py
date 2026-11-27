"""Render four vehicle previews and forward selections without network I/O."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QGridLayout, QPushButton, QWidget

from .i18n import Text
from .local_preview_source import LocalPreviewSource
from .models import Vehicle
from .preview_card import PreviewCard

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
        self,
        tr: Text,
        select: Callable[[str], None],
        *,
        test_images: bool = False,
        local_directory: str | None = None,
    ) -> None:
        """Create the four slots and connect each to the shared vehicle selection."""
        super().__init__()
        self._tr = tr
        self._select = select
        self._test_images = test_images
        self._selected = ''
        self._layout_selection: tuple[bool, str] | None = None
        self._vehicles: dict[str, str] = {}
        self._cards: dict[str, PreviewCard] = {}
        self._test_frames: dict[str, QPixmap] = {}
        self._grid = QGridLayout(self)
        layout = self._grid
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for index, number in enumerate(_NUMBERS):
            card = PreviewCard(number, tr('camera_waiting'), self)
            card.clicked.connect(lambda _checked, key=number: self._choose(key))
            if test_images:
                self._test_frames[number] = _test_image(number, index)
            layout.addWidget(card, index // 2, index % 2)
            self._cards[number] = card
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        self._expand = QPushButton(tr('camera_expand'), self)
        self._expand.setCheckable(True)
        self._expand.toggled.connect(self._show_selection)
        layout.addWidget(self._expand, 2, 0, 1, 2)
        self._source = (
            LocalPreviewSource(Path(local_directory))
            if local_directory and not test_images
            else None
        )
        self._refresh = QTimer(self)
        self._refresh.setInterval(200)
        self._refresh.timeout.connect(self._update_images)
        if self._source:
            self._refresh.start()
        self.present((), '')

    def present(self, vehicles: tuple[Vehicle, ...], selected: str) -> None:
        """Associate each registered number with its snapshot ID and highlight it."""
        self._vehicles = {vehicle.number: vehicle.id for vehicle in vehicles}
        self._selected = selected
        for number, card in self._cards.items():
            vehicle_id = self._vehicles.get(number)
            card.setEnabled(vehicle_id is not None)
            card.setChecked(vehicle_id is not None and vehicle_id == selected)

        self._expand.setEnabled(selected != '' and selected in self._vehicles.values())
        if not self._expand.isEnabled():
            self._expand.setChecked(False)
        self._show_selection(self._expand.isChecked())
        self._update_images()

    def _update_images(self) -> None:
        for number, card in self._cards.items():
            cells = (
                self._source.read(number)
                if self._source and number in self._vehicles
                else None
            )
            if cells is not None:
                image = QImage(cells, 16, 12, 16, QImage.Format.Format_Grayscale8)
                frame = QPixmap.fromImage(image)
                status = 'camera_masked_live'
            elif self._test_images:
                frame = self._test_frames[number]
                status = 'camera_test_image'
            else:
                frame = QPixmap()
                status = 'camera_waiting'
            card.present(frame, self._tr(status))

    def _show_selection(self, expanded: bool) -> None:
        self._expand.setText(self._tr('camera_grid' if expanded else 'camera_expand'))
        layout_selection = (expanded, self._selected if expanded else '')
        if self._layout_selection == layout_selection:
            return
        self._layout_selection = layout_selection
        for index, (number, card) in enumerate(self._cards.items()):
            self._grid.removeWidget(card)
            visible = not expanded or self._vehicles.get(number) == self._selected
            card.setVisible(visible)
            card.set_expanded(expanded)
            if expanded and visible:
                self._grid.addWidget(card, 0, 0, 2, 2)
            elif not expanded:
                self._grid.addWidget(card, index // 2, index % 2)

    def _choose(self, number: str) -> None:
        vehicle_id = self._vehicles.get(number)
        if vehicle_id is not None:
            self._select(vehicle_id)
