"""Main window for the BiMarz desktop GUI.

PySide6 main window integrating profile management, connection controls,
latency monitoring, and kill-switch controls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent
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
    """Primary BiMarz application window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("BiMarz")
        self.setMinimumSize(800, 600)

        self._profile_store = ProfileStore()
        self._connection_worker: ConnectionWorker | None = None
        self._current_profile: ServerProfile | None = None
        self._closing = False

        self._setup_ui()
        self._refresh_profiles()

    def _setup_ui(self) -> None:
        """Build the main widget hierarchy."""
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([400, 400])

    def _build_left_panel(self) -> QWidget:
        """Build the profile and connection control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._profile_table = ProfileTable()
        self._profile_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._profile_table)

        button_layout = QHBoxLayout()

        self._connect_button = QPushButton("Connect")
        self._connect_button.setEnabled(False)
        self._connect_button.clicked.connect(self._on_connect)

        self._disconnect_button = QPushButton("Disconnect")
        self._disconnect_button.setEnabled(False)
        self._disconnect_button.clicked.connect(self._on_disconnect)

        button_layout.addWidget(self._connect_button)
        button_layout.addWidget(self._disconnect_button)
        layout.addLayout(button_layout)

        self._ks_toggle = KillSwitchToggle()
        layout.addWidget(self._ks_toggle)

        self._status_label = QLabel("Ready")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

        return panel

    def _build_right_panel(self) -> QWidget:
        """Build the latency monitoring panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._latency_chart = LatencyChart()
        layout.addWidget(self._latency_chart)

        return panel

    def _refresh_profiles(self) -> None:
        """Load profiles from storage and update the table."""
        try:
            profiles = self._profile_store.list_profiles()
            self._profile_table.set_profiles(profiles)
            self._status_label.setText(f"Loaded {len(profiles)} profile(s)")
        except Exception as exc:
            logger.exception("Failed to load profiles")
            self._status_label.setText(f"Error loading profiles: {exc}")

    @Slot()
    def _on_selection_changed(self) -> None:
        """Update connection controls after profile selection."""
        profile = self._profile_table.selected_profile()
        self._current_profile = profile
        self._connect_button.setEnabled(profile is not None and not self._worker_is_running())

    @Slot()
    def _on_connect(self) -> None:
        """Start a connection worker for the selected profile."""
        if self._closing or self._worker_is_running():
            return

        profile = self._current_profile
        if profile is None:
            return

        try:
            profiles = self._profile_store.list_profiles()
        except Exception as exc:
            logger.exception("Failed to load profiles for connection")
            self._show_connection_error(str(exc))
            return

        all_profiles = {item.profile_id: item for item in profiles}

        self._connect_button.setEnabled(False)
        self._disconnect_button.setEnabled(True)
        self._status_label.setText(f"Connecting to {profile.remark}...")
        self._latency_chart.clear()

        worker = ConnectionWorker(
            profile=profile,
            all_profiles=all_profiles,
            enable_killswitch=self._ks_toggle.is_checked(),
        )

        worker.connected.connect(self._on_worker_connected)
        worker.disconnected.connect(self._on_worker_disconnected)
        worker.connection_error.connect(self._on_worker_error)
        worker.latency_updated.connect(self._on_latency_updated)
        worker.failover_occurred.connect(self._on_failover_occurred)
        worker.killswitch_triggered.connect(self._on_killswitch_triggered)

        self._connection_worker = worker
        worker.start()

    @Slot()
    def _on_disconnect(self) -> None:
        """Request graceful disconnection."""
        worker = self._connection_worker
        if worker is None or not worker.isRunning():
            self._reset_connection_controls()
            return

        worker.stop()
        self._disconnect_button.setEnabled(False)
        self._status_label.setText("Disconnecting...")

    @Slot(str)
    def _on_worker_connected(self, remark: str) -> None:
        """Handle successful connection notification."""
        self._status_label.setText(f"Connected: {remark}")

    @Slot()
    def _on_worker_disconnected(self) -> None:
        """Handle worker disconnection."""
        self._reset_connection_controls()
        self._status_label.setText("Disconnected")

    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        """Handle a connection error."""
        self._reset_connection_controls()
        self._show_connection_error(message)

    @Slot(str, float, bool)
    def _on_latency_updated(
        self,
        profile_id: str,
        latency_ms: float,
        reachable: bool,
    ) -> None:
        """Update latency visualization and profile status."""
        if reachable and latency_ms >= 0:
            self._latency_chart.add_point(latency_ms)

        self._profile_table.update_latency(
            profile_id,
            latency_ms,
            reachable,
        )

    @Slot(str, str)
    def _on_failover_occurred(self, from_id: str, to_id: str) -> None:
        """Display a failover notification."""
        self._status_label.setText(f"Failover: {from_id} -> {to_id}")

    @Slot(str)
    def _on_killswitch_triggered(self, reason: str) -> None:
        """Handle kill-switch activation notification."""
        self._status_label.setText(f"Kill-switch: {reason}")
        self._reset_connection_controls()
        QMessageBox.warning(
            self,
            "Kill-switch Triggered",
            reason,
        )

    def _worker_is_running(self) -> bool:
        """Return whether the connection worker is currently running."""
        worker = self._connection_worker
        return worker is not None and worker.isRunning()

    def _reset_connection_controls(self) -> None:
        """Restore connection controls to an idle state."""
        self._disconnect_button.setEnabled(False)
        self._connect_button.setEnabled(self._current_profile is not None and not self._closing)

    def _show_connection_error(self, message: str) -> None:
        """Display a connection error to the user."""
        self._status_label.setText(f"Error: {message}")
        QMessageBox.critical(
            self,
            "Connection Error",
            message,
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean worker shutdown before closing the window."""
        self._closing = True

        worker = self._connection_worker
        if worker is not None and worker.isRunning():
            worker.stop()

            if not worker.wait(5000):
                logger.warning("Connection worker did not stop within timeout")

        event.accept()
