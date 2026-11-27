"""Present a local-only action preview alongside the monitoring map."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from .i18n import Text
from .models import Vehicle
from .widgets import button, label

ACTIONS = ('move', 'hold', 'resume', 'return_depot')


class VehicleActionPreview(QWidget):
    """Review one selected vehicle without dispatching or persisting an action."""

    close_requested = pyqtSignal()

    def __init__(self, tr: Text) -> None:
        """Build an in-place popup with a bounded draft and confirmation flow."""
        super().__init__()
        self.setObjectName('tile')
        self._tr = tr
        self._selection: Vehicle | None = None
        self._pending = ''
        content = QVBoxLayout(self)
        heading = QHBoxLayout()
        self._title = label('', 'heading')
        heading.addWidget(self._title, 1)
        close = button(tr('close'))
        close.clicked.connect(self.close_requested)
        heading.addWidget(close)
        content.addLayout(heading)
        content.addWidget(label(tr('action_caption'), 'secondary'))
        self._availability = label('', 'secondary')
        content.addWidget(self._availability)
        controls = QHBoxLayout()
        self._action = QComboBox()
        self._action.setAccessibleName(tr('action_label'))
        for name in ACTIONS:
            self._action.addItem(tr(name), name)
        self._action.currentIndexChanged.connect(self.clear)
        controls.addWidget(self._action, 1)
        self._inspect = button(tr('draft'), 'primary')
        self._inspect.clicked.connect(self._review)
        controls.addWidget(self._inspect)
        self._cancel = button(tr('cancel'))
        self._cancel.clicked.connect(self.clear)
        controls.addWidget(self._cancel)
        self._confirm = button(tr('confirm'), 'primary')
        self._confirm.clicked.connect(self._finish)
        controls.addWidget(self._confirm)
        content.addLayout(controls)
        self._message = label('', 'warning')
        content.addWidget(self._message)
        content.addStretch()
        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape.activated.connect(self.close_requested)
        self.present(None)

    def present(self, vehicle: Vehicle | None) -> None:
        """Bind the popup to the current regular vehicle and discard stale drafts."""
        previous = self._selection
        self._selection = vehicle
        available = vehicle is not None and vehicle.can_preview
        if (
            not available
            or previous is None
            or vehicle is None
            or (previous.id, previous.number) != (vehicle.id, vehicle.number)
        ):
            self.clear()
        self._title.setText(
            f'{vehicle.number} · {self._tr("preview_request")}' if vehicle else ''
        )
        self._availability.setText(
            self._tr('action_details' if available else 'offline_action')
        )
        self._action.setEnabled(available)
        self._inspect.setEnabled(available)

    def focus_action(self) -> None:
        """Focus the action selector when the popup opens."""
        self._action.setFocus(Qt.FocusReason.OtherFocusReason)

    def clear(self) -> None:
        """Clear confirmation and result text without changing the current vehicle."""
        self._pending = ''
        self._message.clear()
        self._set_confirming(False)

    def _set_confirming(self, confirming: bool) -> None:
        self._inspect.setVisible(not confirming)
        self._cancel.setVisible(confirming)
        self._confirm.setVisible(confirming)

    def _review(self) -> None:
        vehicle = self._selection
        if vehicle is None or not vehicle.can_preview:
            return
        self._pending = self._action.currentData()
        self._message.setText(self._tr('preview_confirm', vehicle=vehicle.number))
        self._set_confirming(True)

    def _finish(self) -> None:
        vehicle = self._selection
        action = self._pending
        if vehicle is None or not vehicle.can_preview or not action:
            return
        self.clear()
        self._message.setText(
            self._tr('preview_result', vehicle=vehicle.number, action=self._tr(action))
        )
