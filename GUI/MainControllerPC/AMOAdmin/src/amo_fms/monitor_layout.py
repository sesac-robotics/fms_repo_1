"""Give the map and the camera column independently adjustable space."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QSplitter, QWidget


def map_and_cameras(road_map: QWidget, sidebar: QWidget) -> QSplitter:
    """Start with a wide camera column and keep the map visible when resized."""
    scroll = QScrollArea()
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setWidget(sidebar)
    split = QSplitter(Qt.Orientation.Horizontal)
    split.setChildrenCollapsible(False)
    split.setHandleWidth(10)
    split.addWidget(road_map)
    split.addWidget(scroll)
    split.setStretchFactor(0, 1)
    split.setStretchFactor(1, 1)
    split.setSizes([740, 860])
    return split
