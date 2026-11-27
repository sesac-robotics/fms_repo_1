"""Render four vehicle previews and forward selections without network I/O."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QResizeEvent,
    QShortcut,
)
from PyQt6.QtWidgets import QGridLayout, QWidget

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
            card.enlarge_requested.connect(lambda key=number: self._enlarge(key))
            if test_images:
                self._test_frames[number] = _test_image(number, index)
            layout.addWidget(card, index // 2, index % 2)
            self._cards[number] = card
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        escape.activated.connect(lambda: self._show_selection(False))
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

        if self._layout_selection != (True, selected):
            self._show_selection(False)
        self._update_images()

    def _update_images(self) -> None:
        for number, card in self._cards.items():
            preview = (
                self._source.read(number)
                if self._source and number in self._vehicles
                else None
            )
            frame = QPixmap()
            status = self._tr('camera_waiting')
            if preview:
                jpeg, count = preview
                image = QImage.fromData(jpeg, 'JPEG')
                if (image.width(), image.height()) == (640, 480):
                    frame = QPixmap.fromImage(image)
                    status = self._tr(
                        'camera_faces_masked' if count else 'camera_no_faces',
                        count=count,
                    )
            elif self._test_images:
                frame = self._test_frames[number]
                status = self._tr('camera_test_image')
            card.present(frame, status)

    def _show_selection(self, expanded: bool) -> None:
        layout_selection = (expanded, self._selected if expanded else '')
        if self._layout_selection == layout_selection:
            return
        self._layout_selection = layout_selection
        for index, (number, card) in enumerate(self._cards.items()):
            self._grid.removeWidget(card)
            visible = not expanded or self._vehicles.get(number) == self._selected
            card.setVisible(visible)
            if expanded and visible:
                self._grid.addWidget(card, 0, 0, 2, 2)
            elif not expanded:
                self._grid.addWidget(card, index // 2, index % 2)
        self._resize_cards()

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Scale all visible viewports with the available camera column width."""
        super().resizeEvent(event)
        self._resize_cards()

    def _resize_cards(self) -> None:
        expanded = bool(self._layout_selection and self._layout_selection[0])
        width = self.width() if expanded else (self.width() - self._grid.spacing()) // 2
        height = max(112, (width - 12) * 9 // 16)
        if expanded:
            height = min(430, height)
        for card in self._cards.values():
            card.set_viewport_height(height)

    def _enlarge(self, number: str) -> None:
        self._choose(number)
        if self._vehicles.get(number) == self._selected:
            self._show_selection(True)

    def _choose(self, number: str) -> None:
        vehicle_id = self._vehicles.get(number)
        if vehicle_id is not None:
            self._select(vehicle_id)
