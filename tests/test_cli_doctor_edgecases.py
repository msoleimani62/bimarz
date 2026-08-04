"""Edge-case tests for bimarz doctor — ensures robustness against unexpected failures.

تست‌های edge-case برای bimarz doctor — اطمینان از مقاومت در برابر شکست‌های غیرمنتظره.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from bimarz.config import AppConfig
from bimarz.services.doctor import DoctorService
from bimarz.models import GrpcStatus
from bimarz.xray_manager import BinaryNotFoundError


class TestDoctorEdgeCases:
    """Tests that doctor survives failures in its dependencies."""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(doctor_timeout=2.0)

    def test_doctor_handles_profile_store_exception(self, config: AppConfig) -> None:
        """Doctor should survive even if the profile store is corrupted."""
        with patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")):
            with patch("bimarz.services.doctor.ProfileStore") as MockStore:
                instance = MockStore.return_value
                instance.list_profiles.side_effect = Exception("corrupted store")
                svc = DoctorService(config)
                report = asyncio.run(svc.run())
                assert report.profiles_count == 0

    def test_doctor_survives_when_tcp_probe_raises(self, config: AppConfig) -> None:
        """If probe_tcp_port somehow raises, doctor should not crash."""
        with patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")):
            with patch("bimarz.services.doctor.probe_tcp_port", side_effect=OSError("network unreachable")):
                svc = DoctorService(config)
                report = asyncio.run(svc.run())
                assert report.grpc_status == GrpcStatus.unreachable

    def test_doctor_grpc_endpoint_uses_config_values(self, config: AppConfig) -> None:
        """grpc_endpoint in report should reflect config host/port as a full URI."""
        with patch("bimarz.services.doctor.find_xray_binary", side_effect=BinaryNotFoundError("not found")):
            with patch("bimarz.services.doctor.probe_tcp_port", return_value=False):
                svc = DoctorService(config)
                report = asyncio.run(svc.run())
                assert report.grpc_endpoint == f"http://{config.grpc_host}:{config.grpc_port}"
