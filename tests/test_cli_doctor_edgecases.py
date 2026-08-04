"""
Edge-case tests for bimarz.cli doctor functionality.
"""

from __future__ import annotations

import argparse

import pytest
from bimarz.commands.doctor import _doctor_timeout_seconds
from bimarz.constants import DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR


class TestDoctorTimeoutEdgeCases:
    """Edge-case tests for timeout resolution."""

    def test_negative_cli_flag_is_accepted(self) -> None:
        args = argparse.Namespace(doctor_timeout=-1.0)

        result = _doctor_timeout_seconds(args)

        assert result == -1.0

    def test_zero_timeout(self) -> None:
        args = argparse.Namespace(doctor_timeout=0.0)

        result = _doctor_timeout_seconds(args)

        assert result == 0.0

    def test_float_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR,
            "1.5",
        )

        args = argparse.Namespace(doctor_timeout=None)

        result = _doctor_timeout_seconds(args)

        assert result == 1.5

    def test_empty_env_var_falls_back(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR,
            "",
        )

        args = argparse.Namespace(doctor_timeout=None)

        result = _doctor_timeout_seconds(args)

        assert result is not None

    def test_missing_attribute_does_not_crash(self) -> None:
        args = argparse.Namespace()

        result = _doctor_timeout_seconds(args)

        assert result is not None
