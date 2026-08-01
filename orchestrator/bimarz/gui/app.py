"""Entry point for the bimarz desktop GUI."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from bimarz.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def run(argv: list[str] | None = None) -> int:
    """Start the Qt event loop and show the main window."""
    app = QApplication(sys.argv if argv is None else argv)

    app.setApplicationName("BiMarz")
    app.setApplicationDisplayName("BiMarz")
    app.setOrganizationName("BiMarz")

    try:
        window = MainWindow()
        window.show()

        return app.exec()

    except Exception:
        logger.exception("GUI startup failed")
        return 1
