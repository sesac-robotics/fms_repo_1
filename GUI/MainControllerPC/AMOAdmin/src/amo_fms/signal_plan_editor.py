"""Edit one signal's phase durations and build the matching PLAN command."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QGridLayout, QWidget

from .i18n import Text
from .widgets import label

# (translation key, minimum s, maximum s) in PLAN order: north green, east
# green, north yellow, all red, east yellow. The ranges mirror the firmware's
# signal_timing.h and Main Control's SignalCommand; change all three.
FIELDS = (
    ('signal_north_green', 3.0, 120.0),
    ('signal_east_green', 3.0, 120.0),
    ('signal_north_yellow', 2.0, 10.0),
    ('signal_all_red', 1.0, 10.0),
    ('signal_east_yellow', 2.0, 10.0),
)
# Fields every board of a coordinated junction shares: north-south green and
# yellow (both boards run them together) and the all red.
SHARED = (0, 2, 3)
EAST_GREEN, EAST_YELLOW = 1, 4
_PARTNER_MAX_MS = 130_000


def plan_command(seconds: tuple[float, ...], partner_ms: int = 0) -> str | None:
    """Return 'PLAN <ms x6>' for the five durations, or None if any is unsafe.

    ``partner_ms`` is the other board's east green plus east yellow on a
    coordinated junction, so both boards compute the same cycle; 0 otherwise.
    """
    if len(seconds) != len(FIELDS) or not 0 <= partner_ms <= _PARTNER_MAX_MS:
        return None
    millis = [round(value * 1000) for value in seconds]
    for value, (_key, low, high) in zip(millis, FIELDS, strict=True):
        if not low * 1000 <= value <= high * 1000:
            return None
    return 'PLAN ' + ' '.join(str(value) for value in (*millis, partner_ms))


def junction_agrees(
    plans: list[tuple[int, ...]],
    linked: tuple[int, ...] = SHARED,
    east_turns: bool = True,
) -> bool:
    """Whether a coordinated junction's reported plans fit one cycle: the linked
    fields match and, with east turns, each board knows the others' east green
    plus yellow (otherwise no board carries a partner time).
    """
    if len({tuple(plan[i] for i in linked) for plan in plans}) > 1:
        return False
    east = [plan[EAST_GREEN] + plan[EAST_YELLOW] if east_turns else 0 for plan in plans]
    return all(
        plan[5] == sum(east) - own for plan, own in zip(plans, east, strict=True)
    )


class PlanEditor(QWidget):
    """One signal's duration fields; values follow the signal until edited."""

    def __init__(self, tr: Text, title: str, names: dict[str, str]) -> None:
        """``names`` fills the head directions ({'a': ..., 'b': ...}) into the labels."""
        super().__init__()
        self._reported: tuple[int, ...] = ()
        self._editing = False
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.addWidget(label(title, 'heading'), 0, 0, 1, len(FIELDS))
        self._boxes: list[QDoubleSpinBox] = []
        for index, (key, low, high) in enumerate(FIELDS):
            box = QDoubleSpinBox()
            box.setRange(low, high)
            box.setDecimals(1)
            box.setSingleStep(0.5)
            box.setSuffix(' s')
            box.setAccessibleName(tr(key, **names))
            box.valueChanged.connect(self._edited)
            grid.addWidget(label(tr(key, **names), 'secondary', wrap=False), 1, index)
            grid.addWidget(box, 2, index)
            self._boxes.append(box)

    def show_plan(self, plan_ms: tuple[int, ...]) -> None:
        """Track the signal's plan; keep the user's unsaved edits on screen."""
        self._reported = plan_ms
        if not self._editing:
            for box, value in zip(self._boxes, plan_ms, strict=False):
                box.blockSignals(True)
                box.setValue(value / 1000)
                box.blockSignals(False)

    def set_writable(self, writable: bool) -> None:
        """Disable editing when no staff Web session is available."""
        for box in self._boxes:
            box.setEnabled(writable)

    def values(self) -> tuple[float, ...]:
        """Durations currently entered, in seconds."""
        return tuple(box.value() for box in self._boxes)

    def millis(self) -> tuple[int, ...]:
        """Durations currently entered, in milliseconds."""
        return tuple(round(value * 1000) for value in self.values())

    def changed(self, partner_ms: int = 0) -> bool:
        """Whether the entered plan differs from the last reported one."""
        return (*self.millis(), partner_ms) != tuple(self._reported)

    def command(self, partner_ms: int = 0) -> str | None:
        """The PLAN text for the entered values, or None if any is out of range."""
        return plan_command(self.values(), partner_ms)

    def link(self, other: PlanEditor, fields: tuple[int, ...] = SHARED) -> None:
        """Mirror ``fields`` into ``other``: a change on one board's field sets the
        same field on the other (call both ways for a two-way link).
        """
        for index in fields:
            self._boxes[index].valueChanged.connect(other._boxes[index].setValue)

    def _edited(self) -> None:
        self._editing = True
