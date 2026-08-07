"""
Unit tests for the connect command.

تست‌های واحد برای دستور اتصال.
"""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bimarz.commands import connect
from bimarz.config import AppConfig
from bimarz.models import ServerProfile


def _profile(profile_id: str = "p1") -> ServerProfile:
    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark="Test",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-08-08T00:00:00+00:00",
    )


def _args(
    profile_id: str = "p1",
    auto_failover: bool = False,
    killswitch: bool = False,
    debug: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        profile_id=profile_id,
        auto_failover=auto_failover,
        killswitch=killswitch,
        debug=debug,
    )


def _connection_mock() -> MagicMock:
    connection = MagicMock()
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=None)
    connection.start = AsyncMock()
    connection.request_stop = MagicMock()
    return connection


def test_connect_profile_not_found() -> None:
    service = MagicMock()
    service.get.return_value = None

    with (
        patch(
            "bimarz.commands.connect.ProfileService",
            return_value=service,
        ),
        patch("bimarz.commands.connect.console") as console,
        pytest.raises(SystemExit) as exc,
    ):
        connect.run_connect(_args(profile_id="missing"), AppConfig())

    assert exc.value.code == 1
    console.print.assert_called_once()


def test_connect_success_without_options() -> None:
    profile = _profile()

    profile_service = MagicMock()
    profile_service.get.return_value = profile

    connection = _connection_mock()

    with (
        patch(
            "bimarz.commands.connect.ProfileService",
            return_value=profile_service,
        ),
        patch(
            "bimarz.commands.connect.ConnectionService",
            return_value=connection,
        ),
        patch("bimarz.commands.connect.console"),
    ):
        connect.run_connect(_args(), AppConfig())

    connection.start.assert_awaited_once_with(
        profile,
        auto_failover=False,
        killswitch=False,
        all_profiles=[],
    )


def test_connect_success_with_failover_and_killswitch() -> None:
    profile = _profile()
    alternate = _profile("p2")

    profile_service = MagicMock()
    profile_service.get.return_value = profile
    profile_service.list_profiles.return_value = [profile, alternate]

    connection = _connection_mock()

    with (
        patch(
            "bimarz.commands.connect.ProfileService",
            return_value=profile_service,
        ),
        patch(
            "bimarz.commands.connect.ConnectionService",
            return_value=connection,
        ),
        patch("bimarz.commands.connect.console"),
    ):
        connect.run_connect(
            _args(auto_failover=True, killswitch=True),
            AppConfig(),
        )

    profile_service.list_profiles.assert_called_once_with()
    connection.start.assert_awaited_once_with(
        profile,
        auto_failover=True,
        killswitch=True,
        all_profiles=[profile, alternate],
    )


def test_connect_runtime_error_exits() -> None:
    profile = _profile()

    profile_service = MagicMock()
    profile_service.get.return_value = profile

    connection = _connection_mock()
    connection.start = AsyncMock(side_effect=RuntimeError("connection failed"))

    with (
        patch(
            "bimarz.commands.connect.ProfileService",
            return_value=profile_service,
        ),
        patch(
            "bimarz.commands.connect.ConnectionService",
            return_value=connection,
        ),
        patch("bimarz.commands.connect.console") as console,
        pytest.raises(SystemExit) as exc,
    ):
        connect.run_connect(_args(), AppConfig())

    assert exc.value.code == 1
    console.print.assert_called()


def test_connect_debug_reraises_runtime_error() -> None:
    profile = _profile()
    error = RuntimeError("connection failed")

    profile_service = MagicMock()
    profile_service.get.return_value = profile

    connection = _connection_mock()
    connection.start = AsyncMock(side_effect=error)

    with (
        patch(
            "bimarz.commands.connect.ProfileService",
            return_value=profile_service,
        ),
        patch(
            "bimarz.commands.connect.ConnectionService",
            return_value=connection,
        ),
        pytest.raises(RuntimeError, match="connection failed"),
    ):
        connect.run_connect(_args(debug=True), AppConfig())
