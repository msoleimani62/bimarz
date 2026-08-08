"""
Unit tests for application configuration.

تست‌های واحد تنظیمات برنامه.
"""

from __future__ import annotations

import os

from bimarz.config import AppConfig


def test_config_defaults_are_valid() -> None:
    config = AppConfig()

    assert config.grpc_host
    assert config.grpc_port > 0
    assert config.engine_retries >= 0
    assert config.engine_retry_delay >= 0


def test_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("BIMARZ_GRPC_HOST", "10.0.0.2")
    monkeypatch.setenv("BIMARZ_GRPC_PORT", "12345")
    monkeypatch.setenv("BIMARZ_ENGINE_RETRIES", "7")
    monkeypatch.setenv("BIMARZ_ENGINE_RETRY_DELAY", "0.25")

    config = AppConfig.from_env()

    assert config.grpc_host == "10.0.0.2"
    assert config.grpc_port == 12345
    assert config.engine_retries == 7
    assert config.engine_retry_delay == 0.25


def test_config_ignores_unrelated_environment(monkeypatch) -> None:
    monkeypatch.delenv("BIMARZ_GRPC_HOST", raising=False)
    monkeypatch.delenv("BIMARZ_GRPC_PORT", raising=False)

    config = AppConfig.from_env()

    assert config.grpc_host
    assert isinstance(config.grpc_port, int)


def test_config_from_env_does_not_mutate_process_environment() -> None:
    before = dict(os.environ)

    AppConfig.from_env()

    assert dict(os.environ) == before
