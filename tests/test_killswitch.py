"""Tests for bimarz.killswitch_manager.

Pure logic tests — no real iptables execution needed.

تست‌های bimarz.killswitch_manager.

فقط تست منطق — بدون اجرای واقعی iptables.
"""

from __future__ import annotations

import logging

import pytest
from bimarz.engine import EngineNotBuiltError
from bimarz.killswitch_manager import KillSwitchManager
from bimarz.models import KillSwitchState, KillSwitchWatcherState

from bimarz import _engine_core


def test_initial_state_is_inactive() -> None:
    manager = KillSwitchManager()
    assert manager.state.active is False
    assert manager.state.kernel_capable is False


def test_probe_kernel_capability_does_not_crash() -> None:
    manager = KillSwitchManager()
    result = manager.probe_kernel_capability()
    assert isinstance(result, bool)


def test_activate_sets_state_active() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0")
    assert manager.state.active is True


def test_activate_with_uid_sets_uid_in_state() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0", xray_uid=1000)
    assert manager.state.active is True
    assert manager.state.xray_uid == 1000


def test_deactivate_sets_state_inactive() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0")
    manager.deactivate()
    assert manager.state.active is False


def test_deactivate_keeps_kernel_state_when_rule_removal_fails(
    monkeypatch,
    caplog,
) -> None:
    """Keeps the kill-switch active when kernel rule removal fails.

    در صورت شکست حذف قوانین کرنل، kill-switch را فعال نگه می‌دارد.
    """

    manager = KillSwitchManager()
    manager._state = KillSwitchState(
        kernel_capable=True,
        active=True,
        interface="eth0",
        xray_uid=1000,
    )

    def fail_remove_killswitch_rules(interface: str, xray_uid: int | None) -> None:
        """Simulates a kernel rule removal failure.

        شکست حذف قوانین کرنل را شبیه‌سازی می‌کند.
        """
        raise RuntimeError("simulated rule removal failure")

    monkeypatch.setattr(
        _engine_core,
        "remove_killswitch_rules",
        fail_remove_killswitch_rules,
    )

    with caplog.at_level(logging.ERROR, logger="bimarz.killswitch_manager"):
        manager.deactivate()

    assert manager.state.active is True
    assert manager.state.kernel_capable is True
    assert manager.state.interface == "eth0"
    assert manager.state.xray_uid == 1000
    assert "Failed to remove kernel kill-switch rules" in caplog.text


def test_process_watcher_detects_dead_process() -> None:
    manager = KillSwitchManager()
    call_count = 0

    def fake_poll() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count < 3

    manager.start_process_watcher(poll_fn=fake_poll, interval_seconds=0.01)
    manager._watcher_thread.join(timeout=1.0)
    assert manager.is_watcher_alive() is False


def test_process_watcher_stays_alive_while_process_lives() -> None:
    manager = KillSwitchManager()
    call_count = 0

    def fake_poll() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count < 10

    manager.start_process_watcher(poll_fn=fake_poll, interval_seconds=0.01)
    import time

    time.sleep(0.05)
    assert manager.is_watcher_alive() is True
    manager.stop_process_watcher()
    assert manager.is_watcher_alive() is False


def test_process_watcher_rejects_non_positive_interval() -> None:
    manager = KillSwitchManager()

    with pytest.raises(ValueError, match="interval_seconds"):
        manager.start_process_watcher(
            poll_fn=lambda: True,
            interval_seconds=0,
        )


def test_process_watcher_does_not_create_duplicate_thread() -> None:
    manager = KillSwitchManager()
    call_count = 0

    def fake_poll() -> bool:
        nonlocal call_count
        call_count += 1
        return True

    manager.start_process_watcher(
        poll_fn=fake_poll,
        interval_seconds=0.01,
    )

    first_thread = manager._watcher_thread

    manager.start_process_watcher(
        poll_fn=fake_poll,
        interval_seconds=0.01,
    )

    assert manager._watcher_thread is first_thread
    manager.stop_process_watcher()


def test_process_watcher_logs_poll_exception(caplog) -> None:
    manager = KillSwitchManager()

    def failing_poll() -> bool:
        raise RuntimeError("watcher failure")

    with caplog.at_level(
        logging.ERROR,
        logger="bimarz.killswitch_manager",
    ):
        manager.start_process_watcher(
            poll_fn=failing_poll,
            interval_seconds=0.01,
        )
        manager._watcher_thread.join(timeout=1.0)

    assert manager.is_watcher_alive() is False
    assert "Kill-switch process watcher failed" in caplog.text


def test_activate_falls_back_when_kernel_extension_is_missing(monkeypatch) -> None:
    manager = KillSwitchManager()

    monkeypatch.setattr(
        manager,
        "probe_kernel_capability",
        lambda: True,
    )

    import bimarz._engine_core as engine_core

    monkeypatch.setattr(
        engine_core,
        "apply_killswitch_rules",
        lambda interface, xray_uid: (_ for _ in ()).throw(EngineNotBuiltError("missing extension")),
    )

    manager.activate(interface="eth0", xray_uid=1000)

    assert manager.state.active is True
    assert manager.state.kernel_capable is False
    assert manager.state.interface == "eth0"
    assert manager.state.xray_uid == 1000


def test_process_watcher_marks_trigger_on_dead_process() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0")

    manager.start_process_watcher(
        poll_fn=lambda: False,
        interval_seconds=0.01,
    )

    thread = manager._watcher_thread
    assert thread is not None
    thread.join(timeout=1.0)

    assert manager.is_watcher_alive() is False
    assert manager.is_triggered() is True
    assert manager.watcher_state is KillSwitchWatcherState.PROCESS_DIED
    assert manager.trigger_reason == "xray-core unexpectedly stopped"
    assert manager.state.active is True


def test_process_watcher_marks_trigger_on_poll_exception() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0")

    def failing_poll() -> bool:
        raise RuntimeError("watcher failure")

    manager.start_process_watcher(
        poll_fn=failing_poll,
        interval_seconds=0.01,
    )

    thread = manager._watcher_thread
    assert thread is not None
    thread.join(timeout=1.0)

    assert manager.is_watcher_alive() is False
    assert manager.is_triggered() is True
    assert manager.watcher_state is KillSwitchWatcherState.PROCESS_DIED
    assert manager.trigger_reason == "Xray liveness check failed: watcher failure"
    assert manager.state.active is True


def test_process_watcher_cannot_restart_after_trigger() -> None:
    manager = KillSwitchManager()
    manager.activate(interface="eth0")

    manager.start_process_watcher(
        poll_fn=lambda: False,
        interval_seconds=0.01,
    )

    thread = manager._watcher_thread
    assert thread is not None
    thread.join(timeout=1.0)

    assert manager.is_triggered() is True
    assert manager.watcher_state is KillSwitchWatcherState.PROCESS_DIED

    with pytest.raises(
        RuntimeError,
        match="cannot restart after a trigger",
    ):
        manager.start_process_watcher(
            poll_fn=lambda: True,
            interval_seconds=0.01,
        )
