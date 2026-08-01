"""Tests for bimarz.killswitch_manager.

Pure logic tests — no real iptables execution needed.

تست‌های bimarz.killswitch_manager.

فقط تست منطق — بدون اجرای واقعی iptables.
"""

from __future__ import annotations

from bimarz.killswitch_manager import KillSwitchManager, KillSwitchTriggeredError


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
