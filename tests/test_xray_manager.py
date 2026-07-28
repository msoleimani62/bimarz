"""Tests for bimarz.xray_manager.

Uses real short-lived shell-script "fake binaries" written to tmp_path
instead of mocking subprocess internals — this exercises the actual
subprocess.Popen code path (closer to reality than a mock) while staying
fully offline and fast, the same tradeoff made throughout
open-downloader-cli's tests.

تست‌های bimarz.xray_manager.

از "باینری‌های جعلی" واقعی و کوتاه‌عمر به‌شکل اسکریپت شل که در tmp_path
نوشته می‌شوند استفاده می‌کند به‌جای mock کردن داخل subprocess — این کار
مسیر واقعی subprocess.Popen را اجرا می‌کند (نزدیک‌تر به واقعیت از یک mock)
و در عین حال کاملاً آفلاین و سریع می‌ماند، همان معامله‌ای که در کل تست‌های
open-downloader-cli انجام شده.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bimarz.xray_manager import (
    ProcessAlreadyRunningError,
    XrayManagerError,
    XrayProcess,
    find_xray_binary,
    get_xray_version,
)


def _write_fake_binary(path: Path, script_body: str) -> Path:
    path.write_text(f"#!/bin/sh\n{script_body}\n")
    path.chmod(0o755)
    return path


def test_find_xray_binary_returns_none_when_missing(tmp_path: Path) -> None:
    missing = tmp_path / "no_such_binary"
    assert find_xray_binary(explicit_path=str(missing)) is None


def test_find_xray_binary_returns_path_when_present(tmp_path: Path) -> None:
    binary = _write_fake_binary(tmp_path / "xray", "echo ok")
    assert find_xray_binary(explicit_path=str(binary)) == binary


def test_get_xray_version_returns_first_line(tmp_path: Path) -> None:
    binary = _write_fake_binary(
        tmp_path / "xray",
        'echo "Xray 1.8.24 (Xray, Penetrates Everything.) linux/amd64"',
    )
    version = get_xray_version(binary)
    assert version.startswith("Xray 1.8.24")


def test_get_xray_version_raises_on_empty_output(tmp_path: Path) -> None:
    binary = _write_fake_binary(tmp_path / "xray", "true")
    with pytest.raises(XrayManagerError):
        get_xray_version(binary)


def test_get_xray_version_raises_on_nonzero_exit(tmp_path: Path) -> None:
    binary = _write_fake_binary(tmp_path / "xray", "exit 1")
    with pytest.raises(XrayManagerError):
        get_xray_version(binary)


def test_process_lifecycle_start_stop(tmp_path: Path) -> None:
    binary = _write_fake_binary(tmp_path / "xray", "sleep 5")
    proc = XrayProcess(binary_path=binary, config_path=tmp_path / "config.json")

    assert proc.is_alive() is False
    proc.start()
    assert proc.is_alive() is True
    assert proc.pid is not None

    proc.stop()
    assert proc.is_alive() is False
    assert proc.pid is None


def test_process_cannot_start_twice(tmp_path: Path) -> None:
    binary = _write_fake_binary(tmp_path / "xray", "sleep 5")
    proc = XrayProcess(binary_path=binary, config_path=tmp_path / "config.json")

    proc.start()
    with pytest.raises(ProcessAlreadyRunningError):
        proc.start()
    proc.stop()


def test_stop_on_never_started_process_is_a_safe_noop(tmp_path: Path) -> None:
    proc = XrayProcess(binary_path=tmp_path / "xray", config_path=tmp_path / "config.json")
    proc.stop()  # must not raise
    assert proc.is_alive() is False
