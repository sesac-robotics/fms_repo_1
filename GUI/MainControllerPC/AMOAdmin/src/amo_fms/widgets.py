"""Small reusable widgets shared by the fleet preview pages."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .config import Config
from .i18n import Text

LANGUAGE_NAMES = {'ko': '한국어', 'en': 'English', 'zh-Hans': '简体中文'}


def label(text: str, role: str = '', wrap: bool = True) -> QLabel:
    """Create a plain-text Qt label with an optional style role."""
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    result.setObjectName(role)
    result.setWordWrap(wrap)
    return result


def button(text: str, role: str = '') -> QPushButton:
    """Create a button with literal translated text and an optional palette role."""
    result = QPushButton(text.replace('&', '&&'))
    result.setObjectName(role)
    result.setAccessibleName(text)
    return result


def panel(role: str = 'tile') -> tuple[QWidget, QVBoxLayout]:
    """Create one themed content surface and its owned vertical layout."""
    result = QWidget()
    result.setObjectName(role)
    layout = QVBoxLayout(result)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(9)
    return result, layout


def language_select(chosen: str, tr: Text) -> QComboBox:
    """Expose the three supported locales by their own names."""
    combo = QComboBox()
    combo.setAccessibleName(tr('language'))
    for value, title in LANGUAGE_NAMES.items():
        combo.addItem(title, value)
    combo.setCurrentIndex(combo.findData(chosen))
    return combo


def theme_select(chosen: str, tr: Text) -> QComboBox:
    """Expose the approved light and dark modes."""
    combo = QComboBox()
    combo.setAccessibleName(tr('theme'))
    for value in ('light', 'dark'):
        combo.addItem(tr(value), value)
    combo.setCurrentIndex(combo.findData(chosen))
    return combo


class FitImage(QLabel):
    """Display a map image without changing its aspect ratio or layout bounds."""

    def __init__(self, source: Path, description: str, unavailable: str = '') -> None:
        """Load one image and show a text explanation when it cannot be opened."""
        super().__init__(unavailable)
        self._texture = QPixmap(str(source))
        self.setAccessibleName(description)
        self.setToolTip(description)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Scale down or up within the available map pane."""
        super().resizeEvent(event)
        if not self._texture.isNull():
            self.setPixmap(
                self._texture.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


def brand(config: Config, theme: str, size: int = 146) -> QLabel:
    """Build the approved AMO wordmark and Pinky Pro badge from the shared art."""
    badge = QLabel('AMO')
    badge.setObjectName('brand')
    badge.setAccessibleName('AMO')
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setFixedSize(size, 41)
    art = QPixmap(str(config.asset('logo', 'ko', theme)))
    if not art.isNull():
        badge.setPixmap(
            art.scaled(
                QSize(size - 12, 40),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    return badge
