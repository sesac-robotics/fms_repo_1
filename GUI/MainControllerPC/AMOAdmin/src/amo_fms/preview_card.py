"""Paint a camera frame independently of its selectable card caption."""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


class PreviewSurface(QWidget):
    """Keep the complete frame visible inside a dedicated letterboxed viewport."""

    def __init__(self, waiting: str, parent: QWidget) -> None:
        """Create a passive image surface inside a clickable card."""
        super().__init__(parent)
        self._waiting = waiting
        self._frame = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_frame(self, frame: QPixmap) -> None:
        """Replace the current frame, or show the waiting state for a null pixmap."""
        self._frame = frame
        self.update()

    def frame_rect(self) -> QRect:
        """Return the centered, aspect-preserving frame rectangle in widget pixels."""
        size = self._frame.size().scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio
        )
        return QRect(
            (self.width() - size.width()) // 2,
            (self.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )

    def paintEvent(self, _event: QPaintEvent | None) -> None:
        """Paint the viewport independently of Qt button icon dimensions."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#1b1d24'))
        if self._frame.isNull():
            painter.setPen(QColor('#e1e4ed'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._waiting)
        else:
            painter.drawPixmap(self.frame_rect(), self._frame)
        painter.end()


class PreviewCard(QPushButton):
    """Keep the vehicle caption outside the video and preserve keyboard selection."""

    def __init__(self, number: str, waiting: str, parent: QWidget) -> None:
        """Create a dedicated image surface followed by one status caption."""
        super().__init__(parent)
        self._number = number
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.surface = PreviewSurface(waiting, self)
        self._caption = QLabel(self)
        self._caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._caption.setTextFormat(Qt.TextFormat.PlainText)
        self._caption.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)
        layout.addWidget(self.surface)
        layout.addWidget(self._caption)
        self.set_viewport_height(112)

    def present(self, frame: QPixmap, status: str) -> None:
        """Render the frame and expose the vehicle and state to accessibility tools."""
        self.surface.set_frame(frame)
        text = f'{self._number} · {status}'
        self._caption.setText(text)
        self.setAccessibleName(text)

    def set_viewport_height(self, height: int) -> None:
        """Reserve the requested viewport height and keep the caption below it."""
        if self.surface.minimumHeight() != height:
            self.surface.setFixedHeight(height)
            self.setFixedHeight(self.sizeHint().height())

    def sizeHint(self) -> QSize:
        """Keep the image and caption reachable at the application's minimum width."""
        return QSize(
            140, self.surface.minimumHeight() + self._caption.sizeHint().height() + 17
        )

    def minimumSizeHint(self) -> QSize:
        """Allow both columns to share a narrow right-hand panel."""
        return self.sizeHint()
