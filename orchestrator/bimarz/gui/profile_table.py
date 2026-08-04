"""QTableWidget showing saved server profiles with live latency.

جدول QTableWidget برای نمایش پروفایل‌های سرور ذخیره‌شده با latency زنده.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

if TYPE_CHECKING:
    from bimarz.models import ServerProfile


class ProfileTable(QTableWidget):
    """A table widget that displays profiles and their last-known latency.

    یک ویجت جدول که پروفایل‌ها و آخرین latency شناخته‌شده‌شان را نمایش می‌دهد.
    """

    _COLUMN_REMARK: Final = 0
    _COLUMN_ADDRESS: Final = 1
    _COLUMN_LATENCY: Final = 2
    _COLUMN_STATUS: Final = 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Remark", "Address", "Latency", "Status"])

        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            self._COLUMN_LATENCY,
            QHeaderView.ResizeToContents,
        )

        self.verticalHeader().hide()

        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self._profiles: list[ServerProfile] = []

    def set_profiles(self, profiles: list[ServerProfile]) -> None:
        """Populate the table with profiles (latency cleared to '—')."""
        self.setSortingEnabled(False)

        self._profiles = profiles
        self.clearSelection()
        self.setRowCount(len(profiles))

        for row, profile in enumerate(profiles):
            self.setItem(
                row,
                self._COLUMN_REMARK,
                QTableWidgetItem(profile.remark),
            )

            address = f"{profile.outbound_config.get('address', '?')}:{profile.outbound_config.get('port', '?')}"

            self.setItem(
                row,
                self._COLUMN_ADDRESS,
                QTableWidgetItem(address),
            )

            self.setItem(
                row,
                self._COLUMN_LATENCY,
                QTableWidgetItem("—"),
            )

            self.setItem(
                row,
                self._COLUMN_STATUS,
                QTableWidgetItem("Pending"),
            )

        self.setSortingEnabled(True)

    def update_latency(
        self,
        profile_id: str,
        latency_ms: float | None,
        reachable: bool,
    ) -> None:
        """Update the latency and status cells for a single profile."""
        for row, profile in enumerate(self._profiles):
            if profile.profile_id != profile_id:
                continue

            latency_item = self.item(row, self._COLUMN_LATENCY)
            status_item = self.item(row, self._COLUMN_STATUS)

            if latency_item is None or status_item is None:
                return

            if reachable and latency_ms is not None:
                latency_item.setText(f"{latency_ms:.0f} ms")
                latency_item.setForeground(QBrush(QColor("darkgreen")))

                status_item.setText("Online")
                status_item.setForeground(QBrush(QColor("darkgreen")))
            else:
                latency_item.setText("—")
                latency_item.setForeground(QBrush(QColor("red")))

                status_item.setText("Offline")
                status_item.setForeground(QBrush(QColor("red")))

            break

    def selected_profile(self) -> ServerProfile | None:
        """Return the currently selected profile, or None."""
        selected = self.selectedItems()
        if not selected:
            return None

        row = selected[0].row()

        if 0 <= row < len(self._profiles):
            return self._profiles[row]

        return None
