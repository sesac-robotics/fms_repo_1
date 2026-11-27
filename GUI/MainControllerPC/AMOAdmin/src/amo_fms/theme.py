"""AMO contrast-tested light and dark palettes for the PyQt surface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    """The Figma color roles used by Qt controls and status labels."""

    bg: str
    card: str
    header: str
    text: str
    soft: str
    stroke: str
    primary: str
    primary_text: str
    highlight: str
    focus: str
    warning: str
    badge: str


LIGHT = Palette(
    '#F5EFF6',
    '#FCF9FC',
    '#EFE5F1',
    '#35273D',
    '#56465D',
    '#CDBED1',
    '#432C4D',
    '#FCF9FC',
    '#F5DEEC',
    '#5444B8',
    '#89500D',
    '#F3E8F5',
)
DARK = Palette(
    '#1A1321',
    '#2C2234',
    '#33243D',
    '#F0E3F2',
    '#DECFE2',
    '#52415D',
    '#FFABD0',
    '#2B1627',
    '#4D3049',
    '#BBAAFF',
    '#F7CD8A',
    '#302038',
)


def palette(mode: str) -> Palette:
    """Select the approved Figma palette."""
    return DARK if mode == 'dark' else LIGHT


def stylesheet(p: Palette) -> str:
    """Apply palette roles, large status labels and an explicit focus indicator."""
    return f"""
    QWidget {{ background: {p.bg}; color: {p.text}; font-size: 14px; }}
    QWidget#rail, QWidget#top {{ background: {p.header}; }}
    QWidget#tile, QWidget#loginCard {{
        background: {p.card}; border: 1px solid {p.stroke}; border-radius: 14px;
    }}
    QWidget#brand {{ background: {p.badge}; border-radius: 8px; }}
    QLabel {{ background: transparent; }}
    QLabel#title {{ font-size: 28px; font-weight: 700; }}
    QLabel#heading {{ font-size: 16px; font-weight: 700; }}
    QLabel#secondary {{ color: {p.soft}; }}
    QLabel#warning {{ color: {p.warning}; font-weight: 700; }}
    QPushButton, QComboBox, QLineEdit {{
        min-height: 35px; padding: 3px 10px; border: 1px solid {p.stroke};
        background: {p.card}; border-radius: 8px; color: {p.text};
    }}
    QLineEdit {{ padding-left: 12px; }}
    QPushButton:hover, QPushButton:checked {{
        background: {p.highlight}; border-color: {p.focus};
    }}
    QPushButton#primary {{
        background: {p.primary}; color: {p.primary_text}; font-weight: 700;
        padding-left: 16px; padding-right: 16px;
    }}
    QPushButton:disabled, QPushButton#primary:disabled {{
        color: {p.soft}; background: {p.header};
    }}
    QPushButton:focus, QComboBox:focus, QLineEdit:focus, QListWidget:focus,
    QTableWidget:focus {{ border: 2px solid {p.focus}; }}
    QCheckBox {{ spacing: 9px; min-height: 25px; }}
    QCheckBox::indicator:checked {{ width: 20px; height: 20px; }}
    QCheckBox::indicator:unchecked {{
        width: 16px; height: 16px; background: {p.card};
        border: 2px solid {p.soft}; border-radius: 4px;
    }}
    QCheckBox::indicator:unchecked:hover, QCheckBox::indicator:unchecked:focus {{
        border-color: {p.focus};
    }}
    QPushButton#cameraConnection {{ min-height: 14px; padding: 0 5px; }}
    QPushButton#navigation {{ text-align: left; padding-left: 13px; }}
    QListWidget, QTableWidget {{
        background: {p.card}; alternate-background-color: {p.bg};
        border: 1px solid {p.stroke}; border-radius: 8px; padding: 2px;
        selection-background-color: {p.highlight}; selection-color: {p.text};
        gridline-color: {p.stroke};
    }}
    QListWidget::item {{ padding: 8px; min-height: 24px; }}
    QHeaderView::section {{
        background: {p.header}; color: {p.text}; font-weight: 700; padding: 9px;
        border: 0; border-right: 1px solid {p.stroke};
    }}
    """
