"""Keep confirmed road artwork separate from v0.2 replay coordinates."""

from collections.abc import Callable

from PyQt6.QtWidgets import QCheckBox, QStackedWidget, QVBoxLayout, QWidget

from .config import Config, Preferences
from .i18n import Text
from .map_preview import MapPreview
from .models import Vehicle
from .review_playback import Playback
from .signal_map import SignalMap
from .signal_readings import SignalReading
from .widgets import label


class FleetMap(QWidget):
    """Show the confirmed board or the matching map for demo replay."""

    def __init__(
        self,
        tr: Text,
        config: Config,
        prefs: Preferences,
        open_signal: Callable[[str], None],
    ) -> None:
        """Load both maps; ``open_signal(id)`` runs when a map signal is clicked."""
        super().__init__()
        self._tr = tr
        self._caption = label(tr('map_caption'), 'secondary')
        self._legend = label(tr('map_legend'), 'secondary')
        self._legend.hide()
        self._replay = QCheckBox(tr('show_legacy_replay'))
        self._replay.hide()
        self._replay.toggled.connect(self._select_map)
        self._samples: tuple[Vehicle, ...] = ()
        self._selected = ''
        self._maps = QStackedWidget()
        self._maps.setMinimumHeight(330)
        self._confirmed = SignalMap(
            config.asset('map', prefs.language, prefs.theme),
            tr('map_caption'),
            tr('map_missing'),
            open_signal,
        )
        self._legacy = MapPreview(
            config.asset('legacy_map', prefs.language, prefs.theme),
            tr('legacy_map_caption'),
            tr('map_missing'),
        )
        self._maps.addWidget(self._confirmed)
        self._maps.addWidget(self._legacy)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._caption)
        layout.addWidget(self._replay)
        layout.addWidget(self._maps, 1)
        layout.addWidget(self._legend)

    def show_board(
        self, review: Playback | None, signals: tuple[SignalReading, ...]
    ) -> None:
        """Render review playback and live signal lamps on the confirmed map."""
        self._confirmed.show_signals(signals)
        self._confirmed.present(review)
        if review is not None:
            self._replay.setChecked(False)

    def highlight_review(self, selected: bool) -> None:
        """Highlight the confirmed-map marker for the selected scenario vehicle."""
        self._confirmed.highlight(selected)

    def set_replay_available(self, available: bool) -> None:
        """Offer the legacy frame without switching away from the confirmed map."""
        if not available:
            self._replay.setChecked(False)
        self._replay.setVisible(available)

    def _select_map(self, enabled: bool) -> None:
        self._maps.setCurrentWidget(self._legacy if enabled else self._confirmed)
        self._caption.setText(
            self._tr('legacy_map_caption' if enabled else 'map_caption')
        )
        self._legend.setVisible(enabled)
        self._show_current_samples()

    def show_samples(self, vehicles: tuple[Vehicle, ...], selected: str) -> None:
        """Plot legacy metre samples solely on the v0.2 map."""
        self._samples = vehicles
        self._selected = selected
        self._show_current_samples()

    def _show_current_samples(self) -> None:
        active = self._maps.currentWidget() is self._legacy
        self._legacy.show_samples(self._samples if active else (), self._selected)
