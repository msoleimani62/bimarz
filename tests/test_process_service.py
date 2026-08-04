"""Tests for bimarz.services.process.

Verifies that ProcessService writes JSON to a real temp file on disk and
passes the file path (not the JSON string) to the process factory.

تست‌های bimarz.services.process.

بررسی می‌کند که ProcessService JSON را در یک فایل موقت واقعی روی دیسک
می‌نویسد و مسیر فایل (نه رشته JSON) را به process factory پاس می‌دهد.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bimarz.models import ServerProfile
from bimarz.services.process import ProcessService
from bimarz.xray_manager import BinaryNotFoundError, XrayProcess


def _make_profile() -> ServerProfile:
    return ServerProfile(
        profile_id="test-p0a",
        tag="test",
        remark="Test Server",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-08-04T00:00:00+00:00",
    )


def test_start_writes_config_to_real_file_and_passes_path(tmp_path: Path) -> None:
    """Factory must receive a Path that exists and contains valid JSON."""
    fake_binary = tmp_path / "xray"
    fake_binary.write_text("#!/bin/sh\nsleep 5")
    fake_binary.chmod(0o755)

    def fake_config_builder(**kwargs):
        return '{"log": {"loglevel": "warning"}}'

    captured = []

    def fake_factory(binary_path, config_path):
        captured.append((binary_path, config_path))
        mock_proc = MagicMock(spec=XrayProcess)
        mock_proc.is_running.return_value = False
        return mock_proc

    svc = ProcessService(
        binary_finder=lambda: fake_binary,
        config_builder=fake_config_builder,
        process_factory=fake_factory,
    )

    proc = svc.start(_make_profile())
    assert proc is not None

    assert len(captured) == 1
    binary_path, config_path = captured[0]
    assert Path(binary_path) == fake_binary
    assert isinstance(config_path, Path)
    assert config_path.exists()
    assert config_path.stat().st_size > 0

    content = config_path.read_text(encoding="utf-8")
    assert json.loads(content) == {"log": {"loglevel": "warning"}}

    svc.stop()
    assert not config_path.exists()


def test_start_cleans_up_temp_on_exception(tmp_path: Path) -> None:
    """If start() fails after TemporaryDirectory is created, the directory must be removed from disk."""
    fake_binary = tmp_path / "xray"
    fake_binary.write_text("#!/bin/sh\nsleep 5")
    fake_binary.chmod(0o755)

    def fake_config_builder(**kwargs):
        return '{"log": {"loglevel": "warning"}}'

    captured_path = []

    def failing_factory(binary_path, config_path):
        captured_path.append(config_path)
        raise RuntimeError("factory failure")

    svc = ProcessService(
        binary_finder=lambda: fake_binary,
        config_builder=fake_config_builder,
        process_factory=failing_factory,
    )

    with pytest.raises(RuntimeError, match="factory failure"):
        svc.start(_make_profile())

    assert svc._runtime_dir is None
    assert len(captured_path) == 1
    assert not captured_path[0].exists()
    assert not captured_path[0].parent.exists()


def test_binary_not_found_raises_before_temp_creation() -> None:
    svc = ProcessService(binary_finder=lambda: None)
    with pytest.raises(BinaryNotFoundError):
        svc.start(_make_profile())

