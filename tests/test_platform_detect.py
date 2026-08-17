"""Tests for bimarz.platform_detect.

Uses monkeypatch to fake /proc/mounts and /etc/os-release content instead
of depending on the real host — the same principle as the stub-based
testing already used throughout open-downloader-cli's test suite.

تست‌های bimarz.platform_detect.

از monkeypatch برای جعل محتوای /proc/mounts و /etc/os-release استفاده
می‌کند به‌جای وابستگی به هاست واقعی — همان اصل تست‌نویسی مبتنی بر stub که
در کل مجموعه تست open-downloader-cli استفاده شده.
"""

from __future__ import annotations

import pytest
from bimarz import platform_detect
from bimarz.models import Environment


@pytest.fixture(autouse=True)
def _clear_force_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(platform_detect._FORCE_ENV_VAR, raising=False)


def test_desktop_linux_when_no_android_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: False)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: False)
    assert platform_detect.detect_environment() == Environment.DESKTOP_LINUX


def test_kali_nethunter_detected_via_os_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: True)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: False)
    monkeypatch.setattr(platform_detect, "_os_release_id", lambda: "kali")
    assert platform_detect.detect_environment() == Environment.KALI_NETHUNTER


def test_plain_android_termux_when_not_kali(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: True)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: False)
    monkeypatch.setattr(platform_detect, "_os_release_id", lambda: "ubuntu")
    assert platform_detect.detect_environment() == Environment.ANDROID_TERMUX


def test_wsl_takes_priority_over_android_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    # حتی اگر (نظری) نشانه‌های اندروید هم وجود داشته باشند، WSL باید برنده شود.
    # Even if (hypothetically) Android signals were also present, WSL wins.
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: True)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: True)
    assert platform_detect.detect_environment() == Environment.WSL


def test_force_env_var_overrides_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: False)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: False)
    monkeypatch.setenv(platform_detect._FORCE_ENV_VAR, "kali_nethunter")
    assert platform_detect.detect_environment() == Environment.KALI_NETHUNTER


def test_invalid_force_env_var_falls_back_to_auto_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_detect, "_has_android_kernel_signals", lambda: False)
    monkeypatch.setattr(platform_detect, "_is_wsl", lambda: False)
    monkeypatch.setenv(platform_detect._FORCE_ENV_VAR, "not_a_real_environment")
    assert platform_detect.detect_environment() == Environment.DESKTOP_LINUX


def test_read_text_safe_returns_empty_string_on_missing_file(tmp_path) -> None:
    missing = tmp_path / "does_not_exist"
    assert platform_detect._read_text_safe(missing) == ""
