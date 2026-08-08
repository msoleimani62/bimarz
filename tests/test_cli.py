"""
Tests for the bimarz CLI entry point.

تست‌های نقطه ورود CLI برنامه.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from bimarz import cli
from bimarz.engine import EngineNotBuiltError
from bimarz.errors import get_hint
from bimarz.events import ConnectionEvent


def test_parser_version_flag() -> None:
    parser = cli._build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])

    assert exc.value.code == 0


def test_parser_doctor_options() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(
        [
            "doctor",
            "--xray-bin",
            "/custom/xray",
            "--doctor-timeout",
            "5.5",
        ]
    )

    assert args.command == "doctor"
    assert args.xray_bin == "/custom/xray"
    assert args.doctor_timeout == 5.5


def test_parser_profile_add() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["profile", "add", "vless://example"])

    assert args.command == "profile"
    assert args.profile_command == "add"
    assert args.link == "vless://example"


def test_parser_profile_list() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["profile", "list"])

    assert args.profile_command == "list"


def test_parser_profile_remove() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["profile", "remove", "p1"])

    assert args.profile_command == "remove"
    assert args.profile_id == "p1"


def test_parser_healthcheck() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["healthcheck"])

    assert args.command == "healthcheck"


def test_parser_connect_options() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(
        [
            "connect",
            "p1",
            "--auto-failover",
            "--killswitch",
        ]
    )

    assert args.profile_id == "p1"
    assert args.auto_failover is True
    assert args.killswitch is True


def test_parser_killswitch_enable() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(
        [
            "killswitch",
            "enable",
            "--interface",
            "wg0",
            "--xray-uid",
            "1001",
        ]
    )

    assert args.ks_command == "enable"
    assert args.interface == "wg0"
    assert args.xray_uid == 1001


def test_parser_killswitch_disable() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["killswitch", "disable"])

    assert args.ks_command == "disable"


def test_parser_killswitch_status() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["killswitch", "status"])

    assert args.ks_command == "status"


def test_main_success() -> None:
    with (
        patch.object(sys, "argv", ["bimarz", "healthcheck"]),
        patch("bimarz.cli.AppConfig.from_env") as config_factory,
        patch("bimarz.cli.logging.basicConfig"),
        patch("bimarz.cli.run_healthcheck") as command,
        pytest.raises(SystemExit) as exc,
    ):
        config = config_factory.return_value
        config.log_level = 20
        cli.main()

    assert exc.value.code == 0
    command.assert_called_once()


def test_main_handles_exception_without_debug() -> None:
    with (
        patch.object(sys, "argv", ["bimarz", "healthcheck"]),
        patch("bimarz.cli.AppConfig.from_env") as config_factory,
        patch("bimarz.cli.logging.basicConfig"),
        patch("bimarz.cli.run_healthcheck", side_effect=RuntimeError("boom")),
        patch("bimarz.cli.console") as console,
        pytest.raises(SystemExit) as exc,
    ):
        config = config_factory.return_value
        config.log_level = 20
        cli.main()

    assert exc.value.code == 1
    assert console.print.call_count == 2


def test_main_debug_reraises_exception() -> None:
    with (
        patch.object(sys, "argv", ["bimarz", "--debug", "healthcheck"]),
        patch("bimarz.cli.AppConfig.from_env") as config_factory,
        patch("bimarz.cli.logging.basicConfig"),
        patch("bimarz.cli.run_healthcheck", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        config = config_factory.return_value
        config.log_level = 20
        cli.main()


def test_engine_error_has_hint() -> None:
    hint = get_hint(EngineNotBuiltError("missing"))

    assert hint is not None
    assert "maturin develop" in hint


def test_unknown_error_has_no_hint() -> None:
    assert get_hint(RuntimeError("unknown")) is None


def test_connection_events_are_distinct() -> None:
    events = list(ConnectionEvent)

    assert len(events) == 8
    assert len(set(events)) == 8
