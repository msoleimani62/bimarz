"""
Phase 8 GUI ConnectionWorker lifecycle tests.

These tests require PySide6. They validate stop/cleanup contracts without
starting a real Xray process.

تست‌های چرخه عمر ConnectionWorker فاز ۸.

این تست‌ها به PySide6 نیاز دارند. قراردادهای stop/cleanup را بدون
راه‌اندازی فرآیند واقعی Xray اعتبارسنجی می‌کنند.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("PySide6")

from bimarz.gui.connection_worker import ConnectionWorker, detect_default_interface
from bimarz.models import ServerProfile
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _profile() -> ServerProfile:
    return ServerProfile(
        profile_id="p1",
        tag="p1",
        remark="GUI Profile",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-08-12T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_async_cleanup_propagates_engine_remove_failure(
    qapp: QApplication,
) -> None:
    """Engine outbound cleanup failures must remain observable.
    شکست cleanup مربوط به outbound engine باید قابل مشاهده باقی بماند.
    """
    worker = ConnectionWorker(profile=_profile())

    client = MagicMock()
    client.remove_outbound.side_effect = RuntimeError("grpc unavailable")
    client.close = AsyncMock()

    worker._client = client

    with pytest.raises(RuntimeError, match="remove outbound failed"):
        await worker._async_cleanup()

    client.remove_outbound.assert_called_once()
    client.close.assert_awaited_once()


def test_stop_sets_stop_event(qapp: QApplication) -> None:
    """stop() must mark the worker as requested to stop.
    stop() باید worker را به‌عنوان درخواست‌شده برای توقف علامت بزند.
    """
    worker = ConnectionWorker(profile=_profile())
    assert worker.should_stop() is False
    worker.stop()
    assert worker.should_stop() is True


def test_cleanup_stops_process_and_clears_runtime(qapp: QApplication) -> None:
    """_cleanup must release process and runtime directory ownership.
    _cleanup باید مالکیت process و دایرکتوری runtime را آزاد کند.
    """
    worker = ConnectionWorker(profile=_profile())

    process = MagicMock()
    runtime = MagicMock()
    worker._xray_process = process
    worker._runtime_dir = runtime
    worker._client = None
    worker._loop = None

    worker._ks_manager = MagicMock()
    worker._ks_manager.state = MagicMock(active=False)

    worker._cleanup()

    process.stop.assert_called_once()
    runtime.cleanup.assert_called_once()
    assert worker._xray_process is None
    assert worker._runtime_dir is None


def test_cleanup_logs_killswitch_deactivate_failure(
    qapp: QApplication,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Kill-switch deactivate failure must be logged, not silent.
    شکست deactivate مربوط به kill-switch باید log شود، نه خاموش بماند.
    """
    worker = ConnectionWorker(profile=_profile())
    worker._client = None
    worker._loop = None
    worker._xray_process = None
    worker._runtime_dir = None

    ks = MagicMock()
    ks.state = MagicMock(active=True)
    ks.deactivate.side_effect = RuntimeError("permission denied")
    worker._ks_manager = ks

    with caplog.at_level(logging.ERROR, logger="bimarz.gui.connection_worker"):
        worker._cleanup()

    assert "kill-switch deactivate failed" in caplog.text
    ks.deactivate.assert_called_once()


def test_detect_default_interface_returns_string() -> None:
    """Interface detection must always return a non-empty string.
    تشخیص interface باید همیشه یک رشته غیرخالی برگرداند.
    """
    iface = detect_default_interface()
    assert isinstance(iface, str)
    assert iface
