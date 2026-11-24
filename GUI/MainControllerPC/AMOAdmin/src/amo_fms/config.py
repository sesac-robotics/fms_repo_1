"""FMS runtime configuration and local display preferences."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from PyQt6.QtCore import QSettings

LANGUAGES = ('ko', 'en', 'zh-Hans')
THEMES = ('light', 'dark')
DEFAULT_ENDPOINT = 'http://127.0.0.1:18085'
DEFAULT_ADMIN_WEB = 'http://127.0.0.1:5175'
DEFAULT_IF03_PORT = 18087
DEFAULT_MAP_ROOT = Path(__file__).resolve().parents[5] / 'maps'


def preview_endpoint(value: str) -> str:
    """Accept a path-free HTTPS origin or a local HTTP origin."""
    candidate = value.strip().rstrip('/')
    parts = urlsplit(candidate)
    is_loopback = parts.hostname in {'localhost', '127.0.0.1', '::1'}
    if (
        parts.scheme != 'https'
        and not (parts.scheme == 'http' and is_loopback)
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise ValueError('Use an HTTPS origin or a loopback HTTP origin.')
    _ = parts.port
    return candidate


@dataclass(frozen=True, slots=True)
class Config:
    """Configuration for Web sign-in, IF-03 and shared map assets."""

    endpoint: str
    map_root: Path
    admin_web: str = DEFAULT_ADMIN_WEB
    operations_port: int = DEFAULT_IF03_PORT
    scenario_review: bool = False

    @classmethod
    def from_environment(cls, *, fleet: bool = True) -> Config:
        """Read Web settings and optionally use the fleet TCP port override."""
        port = DEFAULT_IF03_PORT
        if fleet:
            port = int(os.environ.get('AMO_FMS_TCP_PORT', str(port)))
        if not 1 <= port <= 65535:
            raise ValueError('AMO_FMS_TCP_PORT must be a valid TCP port.')
        endpoint = preview_endpoint(os.environ.get('AMO_FMS_API', DEFAULT_ENDPOINT))
        local = urlsplit(endpoint).hostname in {'localhost', '127.0.0.1', '::1'}
        return cls(
            endpoint,
            Path(os.environ.get('AMO_MAP_DIR', str(DEFAULT_MAP_ROOT))).expanduser(),
            preview_endpoint(os.environ.get('AMO_ADMIN_WEB_URL', DEFAULT_ADMIN_WEB)),
            port,
            local and os.environ.get('AMO_SCENARIO_REVIEW') == '1',
        )

    def asset(self, base: str, language: str, theme: str) -> Path:
        """Return the shared palette or localized map image path."""
        suffix = theme if theme in THEMES else 'light'
        locale = language if language in LANGUAGES else 'ko'
        stem = 'amo-logo' if base == 'logo' else f'amode-map-v02-fms-{locale}'
        return self.map_root / f'{stem}-{suffix}.png'


@dataclass(slots=True)
class Preferences:
    """Operating system settings for localization, palette and walkthrough only."""

    settings: QSettings

    @classmethod
    def open(cls) -> Preferences:
        """Open the local display-preference namespace."""
        return cls(QSettings('AMoDE', 'AMO-FMS'))

    @property
    def language(self) -> str:
        """Get a validated application locale."""
        val = self.settings.value('language', 'ko', type=str)
        return val if val in LANGUAGES else 'ko'

    @property
    def theme(self) -> str:
        """Get a validated FMS theme."""
        val = self.settings.value('theme', 'light', type=str)
        return val if val in THEMES else 'light'

    @property
    def walkthrough_enabled(self) -> bool:
        """Return whether the automatic first-use tutorial is enabled."""
        return self.settings.value('walkthrough/enabled', True, type=bool)

    @property
    def should_offer_walkthrough(self) -> bool:
        """Return whether a first successful sign-in should open the tutorial."""
        seen = self.settings.value('walkthrough/seen', False, type=bool)
        return self.walkthrough_enabled and not seen
