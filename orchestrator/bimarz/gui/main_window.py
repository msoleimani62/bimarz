"""Main window for the bimarz desktop GUI.

PySide6 main window integrating profile list, connection controls,
latency chart, and kill-switch toggle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from bimarz.gui.connection_worker import ConnectionWorker
from bimarz.gui.killswitch_toggle import KillSwitchToggle
from bimarz.gui.latency_chart import LatencyChart
from bimarz.gui.profile_table import ProfileTable
from bimarz.profiles import ProfileStore

if TYPE_CHECKING:
    from bimarz.models import ServerProfile

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("BiMarz")
        self.setMinimumSize(800, 600)

        self._profile_store = ProfileStore()
        self._connection_worker: ConnectionWorker | None = None
        self._current_profile: ServerProfile | None = None

        self._setup_ui()
        self._refresh_profiles()

    def _setup_ui(self) -> None:
        """Build the widget hierarchy."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: profile list + controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self._profile_table = ProfileTable()
        self._profile_table.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._profile_table)

        button_layout = QHBoxLayout()

        self._connect_button = QPushButton("Connect")
        self._connect_button.setEnabled(False)
        self._connect_button.clicked.connect(self._on_connect)

        self._disconnect_button = QPushButton("Disconnect")
        self._disconnect_button.setEnabled(False)
        self._disconnect_button.clicked.connect(self._on_disconnect)

        button_layout.addWidget(self._connect_button)
        button_layout.addWidget(self._disconnect_button)

        left_layout.addLayout(button_layout)

        self._ks_toggle = KillSwitchToggle()
        left_layout.addWidget(self._ks_toggle)

        self._status_label = QLabel("Ready")
        self._status_label.setWordWrap(True)
        left_layout.addWidget(self._status_label)

        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel: latency chart
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self._latency_chart = LatencyChart()
        right_layout.addWidget(self._latency_chart)

        splitter.addWidget(right_panel)

        splitter.setSizes([400, 400])

    def _refresh_profiles(self) -> None:
        """Load profiles from store and populate the table."""
        try:
            profiles = self._profile_store.list_profiles()
            self._profile_table.set_profiles(profiles)
            self._status_label.setText(f"Loaded {len(profiles)} profile(s)")
        except Exception as exc:
            logger.exception("Failed to load profiles")
            self._status_label.setText(f"Error loading profiles: {exc}")

    @Slot()
    def _on_selection_changed(self) -> None:
        """Enable connect button when a profile is selected."""
        profile = self._profile_table.selected_profile()
        self._connect_button.setEnabled(profile is not None)
        self._current_profile = profile

    @Slot()
    def _on_connect(self) -> None:
        """Start connection to the selected profile."""
        profile = self._current_profile
        if profile is None:
            return

        self._connect_button.setEnabled(False)
        self._disconnect_button.setEnabled(True)
        self._status_label.setText(f"Connecting to {profile.remark}...")

        all_profiles = {p.profile_id: p for p in self._profile_store.list_profiles()}

        self._connection_worker = ConnectionWorker(
            profile=profile,
            all_profiles=all_profiles,
            enable_killswitch=self._ks_toggle.is_checked(),
        )

        self._connection_worker.connected.connect(self._on_worker_connected)
        self._connection_worker.disconnected.connect(self._on_worker_disconnected)
        self._connection_worker.connection_error.connect(self._on_worker_error)
        self._connection_worker.latency_updated.connect(self._on_latency_updated)
        self._connection_worker.failover_occurred.connect(self._on_failover_occurred)
        self._connection_worker.killswitch_triggered.connect(self._on_killswitch_triggered)

        self._latency_chart.clear()
        self._connection_worker.start()

    @Slot()
    def _on_disconnect(self) -> None:
        """Request graceful disconnection."""
        if self._connection_worker is not None:
            self._connection_worker.stop()
            self._status_label.setText("Disconnecting...")

    @Slot(str)
    def _on_worker_connected(self, remark: str) -> None:
        self._status_label.setText(f"Connected: {remark}")

    @Slot()
    def _on_worker_disconnected(self) -> None:
        self._connect_button.setEnabled(True)
        self._disconnect_button.setEnabled(False)
        self._status_label.setText("Disconnected")

    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        self._connect_button.setEnabled(True)
        self._disconnect_button.setEnabled(False)
        self._status_label.setText(f"Error: {message}")
        QMessageBox.critical(self, "Connection Error", message)

    @Slot(str, float, bool)
    def _on_latency_updated(self, profile_id: str, latency_ms: float, reachable: bool) -> None:
        if reachable and latency_ms >= 0:
            self._latency_chart.add_point(latency_ms)

        self._profile_table.update_latency(profile_id, latency_ms, reachable)

    @Slot(str, str)
    def _on_failover_occurred(self, from_id: str, to_id: str) -> None:
        self._status_label.setText(f"Failover: {from_id} -> {to_id}")

    @Slot(str)
    def _on_killswitch_triggered(self, reason: str) -> None:
        self._status_label.setText(f"Kill-switch: {reason}")
        QMessageBox.warning(self, "Kill-switch Triggered", reason)
        self._connect_button.setEnabled(True)
        self._disconnect_button.setEnabled(False)

    def closeEvent(self, event) -> None:
        """Ensure clean shutdown on window close."""
        if self._connection_worker is not None:
            self._connection_worker.stop()
            self._connection_worker.wait(5000)
        event.accept()
