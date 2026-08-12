"""
Tests for CLI command handlers and lightweight services.

تست هندلرهای CLI و سرویس‌های سبک.
"""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bimarz.commands import connect, healthcheck, killswitch, profile
from bimarz.config import AppConfig
from bimarz.models import ServerProfile
from bimarz.services.health import HealthService
from bimarz.services.killswitch import KillSwitchService
from bimarz.services.profile import ProfileService


def _profile(profile_id: str = "p1") -> ServerProfile:
    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark="Test",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-08-08T00:00:00+00:00",
    )


def test_health_service_empty_store() -> None:
    store = MagicMock()
    store.list_profiles.return_value = []

    result = __import__("asyncio").run(HealthService(store).check_all())

    assert result == []


def test_health_service_checks_all_profiles() -> None:
    profiles = [_profile("p1"), _profile("p2")]
    store = MagicMock()
    store.list_profiles.return_value = profiles

    async def fake_check(profile):
        return {"ok": True, "latency_ms": 12}

    with patch("bimarz.services.health.check_profile_health", side_effect=fake_check):
        result = __import__("asyncio").run(HealthService(store).check_all())

    assert len(result) == 2
    assert result[0][0].profile_id == "p1"
    assert result[1][1]["ok"] is True


def test_killswitch_service_enable_uses_current_uid() -> None:
    manager = MagicMock()

    with patch("bimarz.services.killswitch.get_current_uid", return_value=1234):
        service = KillSwitchService(manager)
        service.enable("tun0")

    manager.activate.assert_called_once_with(interface="tun0", xray_uid=1234)


def test_killswitch_service_enable_uses_explicit_uid() -> None:
    manager = MagicMock()

    with patch("bimarz.services.killswitch.get_current_uid") as get_uid:
        KillSwitchService(manager).enable("tun1", uid=4321)

    get_uid.assert_not_called()
    manager.activate.assert_called_once_with(interface="tun1", xray_uid=4321)


def test_killswitch_service_disable() -> None:
    manager = MagicMock()

    KillSwitchService(manager).disable()

    manager.deactivate.assert_called_once()


def test_killswitch_service_start_watcher_delegates() -> None:
    manager = MagicMock()
    poll_fn = MagicMock()

    KillSwitchService(manager).start_watcher(
        poll_fn=poll_fn,
        interval_seconds=0.25,
    )

    manager.start_process_watcher.assert_called_once_with(
        poll_fn=poll_fn,
        interval_seconds=0.25,
    )


def test_killswitch_service_stop_watcher_delegates() -> None:
    manager = MagicMock()

    KillSwitchService(manager).stop_watcher()

    manager.stop_process_watcher.assert_called_once()


def test_killswitch_service_status_methods() -> None:
    manager = MagicMock()
    manager.state.active = True
    manager.is_watcher_alive.return_value = True

    service = KillSwitchService(manager)

    assert service.is_active() is True
    assert service.is_watcher_alive() is True


def test_profile_service_add_list_remove_get() -> None:
    store = MagicMock()
    profile = _profile()

    with patch("bimarz.services.profile.parse_vless_link", return_value=profile):
        service = ProfileService(store)
        result = service.add_from_link("vless://example")

    assert result is profile
    store.add_profile.assert_called_once_with(profile)

    store.list_profiles.return_value = [profile]
    assert service.list_profiles() == [profile]

    service.remove("p1")
    store.remove_profile.assert_called_once_with("p1")

    store.get_profile.return_value = profile
    assert service.get("p1") is profile


def test_profile_add_command_success() -> None:
    args = argparse.Namespace(link="vless://example")

    service = MagicMock()
    service.add_from_link.return_value = _profile()

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.format_profile_address", return_value="example.com:443"),
        patch("bimarz.commands.profile.console") as console,
    ):
        profile.run_profile_add(args, AppConfig())

    service.add_from_link.assert_called_once_with("vless://example")
    console.print.assert_called_once()


def test_profile_add_command_invalid_link() -> None:
    args = argparse.Namespace(link="invalid")

    service = MagicMock()
    service.add_from_link.side_effect = ValueError("invalid")

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.console") as console,
        pytest.raises(SystemExit) as exc,
    ):
        profile.run_profile_add(args, AppConfig())

    assert exc.value.code == 1
    console.print.assert_called_once()


def test_profile_list_empty() -> None:
    service = MagicMock()
    service.list_profiles.return_value = []

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.console") as console,
    ):
        profile.run_profile_list(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_profile_list_with_profiles() -> None:
    service = MagicMock()
    service.list_profiles.return_value = [_profile()]

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.format_profile_address", return_value="example.com:443"),
        patch("bimarz.commands.profile.console") as console,
    ):
        profile.run_profile_list(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_profile_remove_success() -> None:
    service = MagicMock()

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.console") as console,
    ):
        profile.run_profile_remove(argparse.Namespace(profile_id="p1"), AppConfig())

    service.remove.assert_called_once_with("p1")
    console.print.assert_called_once()


def test_profile_remove_failure() -> None:
    service = MagicMock()
    service.remove.side_effect = RuntimeError("failed")

    with (
        patch("bimarz.commands.profile.ProfileService", return_value=service),
        patch("bimarz.commands.profile.console"),
        pytest.raises(SystemExit) as exc,
    ):
        profile.run_profile_remove(argparse.Namespace(profile_id="p1"), AppConfig())

    assert exc.value.code == 1


def test_healthcheck_no_profiles() -> None:
    service = MagicMock()
    service.check_all = AsyncMock(return_value=[])

    with (
        patch("bimarz.commands.healthcheck.HealthService", return_value=service),
        patch("bimarz.commands.healthcheck.console") as console,
    ):
        healthcheck.run_healthcheck(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_healthcheck_success_and_failure_results() -> None:
    p1 = _profile("p1")
    p2 = _profile("p2")
    service = MagicMock()
    service.check_all = AsyncMock(
        return_value=[
            (p1, {"ok": True, "latency_ms": 20}),
            (p2, RuntimeError("timeout")),
        ]
    )

    with (
        patch("bimarz.commands.healthcheck.HealthService", return_value=service),
        patch("bimarz.commands.healthcheck.format_profile_address", return_value="example.com:443"),
        patch("bimarz.commands.healthcheck.console") as console,
    ):
        healthcheck.run_healthcheck(argparse.Namespace(), AppConfig())

    assert console.print.call_count == 2


def test_healthcheck_unreachable_result() -> None:
    p1 = _profile()

    service = MagicMock()
    service.check_all = AsyncMock(return_value=[(p1, {"ok": False})])

    with (
        patch("bimarz.commands.healthcheck.HealthService", return_value=service),
        patch("bimarz.commands.healthcheck.format_profile_address", return_value="example.com:443"),
        patch("bimarz.commands.healthcheck.console") as console,
    ):
        healthcheck.run_healthcheck(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_killswitch_enable_command() -> None:
    service = MagicMock()

    args = argparse.Namespace(interface="tun0", xray_uid=123)

    with (
        patch("bimarz.commands.killswitch.KillSwitchService", return_value=service),
        patch("bimarz.commands.killswitch.console") as console,
    ):
        killswitch.run_killswitch_enable(args, AppConfig())

    service.enable.assert_called_once_with(interface="tun0", uid=123)
    console.print.assert_called_once()


def test_killswitch_enable_command_gets_uid() -> None:
    service = MagicMock()
    args = argparse.Namespace(interface="tun0", xray_uid=None)

    with (
        patch("bimarz.commands.killswitch.KillSwitchService", return_value=service),
        patch("bimarz.commands.killswitch.get_current_uid", return_value=999),
        patch("bimarz.commands.killswitch.console"),
    ):
        killswitch.run_killswitch_enable(args, AppConfig())

    service.enable.assert_called_once_with(interface="tun0", uid=999)


def test_killswitch_disable_command() -> None:
    service = MagicMock()

    with (
        patch("bimarz.commands.killswitch.KillSwitchService", return_value=service),
        patch("bimarz.commands.killswitch.console") as console,
    ):
        killswitch.run_killswitch_disable(argparse.Namespace(), AppConfig())

    service.disable.assert_called_once()
    console.print.assert_called_once()


def test_killswitch_status_command_active() -> None:
    service = MagicMock()
    service.is_active.return_value = True

    with (
        patch("bimarz.commands.killswitch.KillSwitchService", return_value=service),
        patch("bimarz.commands.killswitch.console") as console,
    ):
        killswitch.run_killswitch_status(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_killswitch_status_command_inactive() -> None:
    service = MagicMock()
    service.is_active.return_value = False

    with (
        patch("bimarz.commands.killswitch.KillSwitchService", return_value=service),
        patch("bimarz.commands.killswitch.console") as console,
    ):
        killswitch.run_killswitch_status(argparse.Namespace(), AppConfig())

    console.print.assert_called_once()


def test_connect_missing_profile() -> None:
    service = MagicMock()
    service.get.return_value = None

    args = argparse.Namespace(
        profile_id="missing",
        auto_failover=False,
        killswitch=False,
        debug=False,
    )

    with (
        patch("bimarz.commands.connect.ProfileService", return_value=service),
        patch("bimarz.commands.connect.console") as console,
        pytest.raises(SystemExit) as exc,
    ):
        __import__("asyncio").run(connect._run_connect_async(args, AppConfig()))

    assert exc.value.code == 1
    console.print.assert_called_once()
