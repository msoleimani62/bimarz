"""Kill-switch toggle widget.

Kill-switch status control widget.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget


class KillSwitchToggle(QWidget):
    """Checkbox widget that controls kill-switch state."""

    toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._active = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._checkbox = QCheckBox(
            "Kill-switch"
        )

        self._checkbox.toggled.connect(
            self._on_toggled
        )

        layout.addWidget(
            self._checkbox
        )

        self._status_label = QLabel()

        layout.addWidget(
            self._status_label
        )

        layout.addStretch()

        self._update_label(False)

    def _on_toggled(self, active: bool) -> None:
        if self._active == active:
            return

        self._active = active

        self.toggled.emit(
            active
        )

        self._update_label(
            active
        )

    def _update_label(self, active: bool) -> None:
        if active:
            self._status_label.setText(
                "armed"
            )
            self._status_label.setProperty(
                "state",
                "active",
            )

        else:
            self._status_label.setText(
                "inactive"
            )
            self._status_label.setProperty(
                "state",
                "inactive",
            )

        self._status_label.style().unpolish(
            self._status_label
        )
        self._status_label.style().polish(
            self._status_label
        )

    def set_checked(
        self,
        active: bool,
    ) -> None:
        """Update state without emitting user signal."""

        self._checkbox.blockSignals(
            True
        )

        self._checkbox.setChecked(
            active
        )

        self._checkbox.blockSignals(
            False
        )

        self._active = active

        self._update_label(
            active
        )

    def is_checked(self) -> bool:
        """Return current kill-switch state."""

        return self._active
