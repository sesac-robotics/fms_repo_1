"""Render four vehicle previews and forward selections without network I/O."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import QDialog, QGridLayout, QVBoxLayout, QWidget

from .camera_connections import CameraConnections
from .i18n import Text
from .local_preview_source import LocalPreviewSource
from .models import Vehicle
from .preview_card import PreviewCard, PreviewSurface
from .widgets import button

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
        self._expanded_number = ''
        self._vehicles: dict[str, Vehicle] = {}
        self._cards: dict[str, PreviewCard] = {}
        self._test_frames: dict[str, QPixmap] = {}
        self._connections = CameraConnections(self)
        self._connections.changed.connect(self._update_images)
        self._buttons = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for index, number in enumerate(_NUMBERS):
            card = PreviewCard(number, tr('camera_waiting'), self)
            card.clicked.connect(lambda _checked, key=number: self._choose(key))
            card.enlarge_requested.connect(lambda key=number: self._enlarge(key))
            if test_images:
                self._test_frames[number] = _test_image(number, index)
            connect = button(tr('camera_connect'), 'cameraConnection')
            connect.clicked.connect(
                lambda _checked, key=number: self._connections.toggle(key)
            )
            card.add_connection_button(connect)
            self._buttons[number] = connect
            layout.addWidget(card, index // 2, index % 2)
            self._cards[number] = card
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        self._viewer = QDialog(self)
        self._viewer.resize(720, 480)
        self._viewer.finished.connect(self._close_viewer)
        self._viewer_surface = PreviewSurface(tr('camera_waiting'), self._viewer)
        QVBoxLayout(self._viewer).addWidget(self._viewer_surface)
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
        self._vehicles = {
            vehicle.number: vehicle
            for vehicle in vehicles
            if vehicle.number in self._cards
        }
        for number, card in self._cards.items():
            vehicle = self._vehicles.get(number)
            card.setEnabled(vehicle is not None)
            card.setChecked(vehicle is not None and vehicle.id == selected)

        if self._expanded_number and self._expanded_number not in self._vehicles:
            self._viewer.close()
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
            vehicle = self._vehicles.get(number)
            state = self._tr.status(vehicle.status) if vehicle else self._tr('unknown')
            card.present(frame, state, status)
            self._update_connection(number, not frame.isNull())

            if number == self._expanded_number:
                self._viewer_surface.set_frame(frame)

    def _update_connection(self, number: str, has_frame: bool) -> None:
        button = self._buttons[number]
        active = self._connections.active(number)
        available = self._source is not None and self._connections.available(number)
        button.setEnabled(active or (available and number in self._vehicles))
        key = 'camera_connect'
        if active:
            key = 'camera_disconnect' if has_frame else 'camera_connecting'
        elif self._connections.failed(number):
            key = 'camera_retry'
        title = self._tr(key)
        button.setText(title)
        button.setAccessibleName(f'{number} · {title}')

    def _enlarge(self, number: str) -> None:
        self._choose(number)
        card = self._cards[number]
        self._expanded_number = number
        self._viewer.setWindowTitle(card.accessibleName())
        self._viewer_surface.set_frame(card.surface.frame)
        self._viewer.show()
        self._viewer.raise_()

    def _close_viewer(self) -> None:
        self._expanded_number = ''
        self._viewer_surface.set_frame(QPixmap())

    def _choose(self, number: str) -> None:
        vehicle = self._vehicles.get(number)
        if vehicle is not None:
            self._select(vehicle.id)
