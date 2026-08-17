"""Tests for bimarz.cli doctor functionality.

Unit tests for doctor timeout resolution, gRPC status reporting,
and error hint generation. No subprocess or network needed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from bimarz.commands.doctor import _doctor_timeout_seconds, _render_doctor_report
from bimarz.config import AppConfig
from bimarz.constants import (
    DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR,
    DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS,
)
from bimarz.models import DoctorReport, Environment, GrpcStatus
from bimarz.services.doctor import DoctorService
from bimarz.xray_manager import BinaryNotFoundError


class TestDoctorTimeoutResolution:
    """Tests for _doctor_timeout_seconds priority logic."""

    def test_cli_flag_takes_highest_priority(self) -> None:
        args = argparse.Namespace()
        args.doctor_timeout = 7.5
        result = _doctor_timeout_seconds(args)
        assert result == 7.5

    def test_env_var_used_when_no_cli_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR, "3.0")
        args = argparse.Namespace()
        args.doctor_timeout = None
        result = _doctor_timeout_seconds(args)
        assert result == 3.0

    def test_default_used_when_nothing_else_set(self) -> None:
        args = argparse.Namespace()
        args.doctor_timeout = None
        os.environ.pop(DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR, None)
        result = _doctor_timeout_seconds(args)
        assert result == DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS

    def test_invalid_env_var_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR, "not-a-number")
        args = argparse.Namespace()
        args.doctor_timeout = None
        result = _doctor_timeout_seconds(args)
        assert result == DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS


class TestDoctorService:
    """Tests for DoctorService.run with mocked dependencies."""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(doctor_timeout=2.0)

    def test_report_shows_binary_not_found(self, config: AppConfig) -> None:
        with patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")):
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.xray_binary_found is False
            assert report.xray_binary_path is None

    def test_report_shows_binary_found_with_version(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", return_value="/usr/bin/xray"),
            patch("bimarz.services.doctor.get_xray_version", return_value="Xray 1.8.24"),
        ):
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.xray_binary_found is True
            assert report.xray_binary_path == "/usr/bin/xray"
            assert report.xray_version == "Xray 1.8.24"

    def test_report_counts_profiles(self, config: AppConfig) -> None:
        mock_profile = MagicMock()
        mock_profile.profile_id = "test-id"
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.ProfileStore") as MockStore,
        ):
            instance = MockStore.return_value
            instance.list_profiles.return_value = [mock_profile, mock_profile]
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.profiles_count == 2

    def test_report_shows_killswitch_inactive_by_default(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.KillSwitchManager") as MockKS,
        ):
            instance = MockKS.return_value
            instance.state.active = False
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.killswitch_active is False

    def test_grpc_status_unreachable_when_tcp_fails(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.probe_tcp_port", return_value=False),
        ):
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.grpc_status == GrpcStatus.unreachable

    def test_grpc_status_listening_when_tcp_ok_but_probe_fails(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.probe_tcp_port", return_value=True),
            patch("bimarz.services.doctor.probe_grpc_with_engine", return_value=False),
        ):
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.grpc_status == GrpcStatus.listening

    def test_grpc_status_responding_when_probe_succeeds(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.probe_tcp_port", return_value=True),
            patch("bimarz.services.doctor.probe_grpc_with_engine", return_value=True),
        ):
            svc = DoctorService(config)
            report = asyncio.run(svc.run())
            assert report.grpc_status == GrpcStatus.responding

    def test_grpc_probe_receives_endpoint_string_not_client(self, config: AppConfig) -> None:
        """probe_grpc_with_engine must receive a URI string, not a client instance."""
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.probe_tcp_port", return_value=True),
            patch("bimarz.services.doctor.probe_grpc_with_engine") as mock_probe,
        ):
            mock_probe.return_value = True
            svc = DoctorService(config)
            asyncio.run(svc.run())
            mock_probe.assert_called_once()
            endpoint = mock_probe.call_args.args[0]
            assert endpoint.startswith("http://")
            assert "127.0.0.1" in endpoint

    def test_explicit_xray_bin_path_passed_through(self, config: AppConfig) -> None:
        with patch("bimarz.services.doctor.find_xray_binary") as mock_find:
            mock_find.return_value = "/custom/xray"
            with patch("bimarz.services.doctor.get_xray_version", return_value="Xray 1.8.24"):
                svc = DoctorService(config)
                asyncio.run(svc.run(xray_bin="/custom/xray"))
                mock_find.assert_called_once_with("/custom/xray")

    def test_custom_timeout_override(self, config: AppConfig) -> None:
        with (
            patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")),
            patch("bimarz.services.doctor.probe_tcp_port") as mock_probe,
        ):
            mock_probe.return_value = False
            svc = DoctorService(config)
            asyncio.run(svc.run(timeout=5.0))
            mock_probe.assert_called_once()
            call_args = mock_probe.call_args
            assert call_args.kwargs.get("timeout") == 5.0


class TestRenderDoctorReport:
    """Tests for _render_doctor_report output."""

    @pytest.fixture
    def console_mock(self):
        with patch("bimarz.commands.doctor.console") as mock:
            yield mock

    def test_shows_version_line(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=False,
            xray_binary_path=None,
            xray_version=None,
            grpc_status=GrpcStatus.not_checked,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "0.2.2" in printed

    def test_shows_binary_not_found_with_hint(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=False,
            xray_binary_path=None,
            xray_version=None,
            grpc_status=GrpcStatus.not_checked,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "not found" in printed
        assert "hint:" in printed

    def test_shows_binary_found_with_version(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.not_checked,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "/usr/bin/xray" in printed
        assert "1.8.24" in printed

    def test_grpc_unreachable_shows_hint(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.unreachable,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "unreachable" in printed
        assert "ensure xray-core is running" in printed

    def test_grpc_listening_shows_build_hint(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.listening,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "listening" in printed
        assert "maturin develop" in printed

    def test_grpc_responding_shows_success(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.responding,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "responding" in printed
        assert "fully responsive" in printed

    def test_shows_profile_count(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.responding,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=5,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "Profiles stored: 5" in printed

    def test_shows_killswitch_active(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.responding,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=True,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "active" in printed

    def test_shows_killswitch_inactive(self, console_mock) -> None:
        report = DoctorReport(
            bimarz_version="0.2.2",
            environment=Environment.DESKTOP_LINUX,
            xray_binary_found=True,
            xray_binary_path="/usr/bin/xray",
            xray_version="Xray 1.8.24",
            grpc_status=GrpcStatus.responding,
            grpc_endpoint="127.0.0.1:10085",
            profiles_count=0,
            killswitch_active=False,
        )
        _render_doctor_report(report)
        printed = " ".join(str(call) for call in console_mock.print.call_args_list)
        assert "inactive" in printed


class TestGrpcStatusEnum:
    """Tests for GrpcStatus enum completeness."""

    def test_all_expected_states_exist(self) -> None:
        assert GrpcStatus.not_checked is not None
        assert GrpcStatus.unreachable is not None
        assert GrpcStatus.listening is not None
        assert GrpcStatus.responding is not None

    def test_backward_compat_aliases(self) -> None:
        assert GrpcStatus.not_checked == GrpcStatus.NOT_CHECKED
        assert GrpcStatus.unreachable == GrpcStatus.UNREACHABLE
        assert GrpcStatus.listening == GrpcStatus.LISTENING
        assert GrpcStatus.responding == GrpcStatus.RESPONDING
