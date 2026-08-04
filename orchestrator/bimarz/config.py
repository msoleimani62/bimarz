"""
Central application configuration.
پیکربندی مرکزی برنامه.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from bimarz.constants import (
    DEFAULT_GRPC_HOST,
    DEFAULT_GRPC_PORT,
    DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS,
    ENGINE_CONNECT_MAX_RETRIES,
    ENGINE_CONNECT_RETRY_DELAY,
    FAILOVER_CHECK_INTERVAL_SECONDS,
)


@dataclass(slots=True)
class AppConfig:
    """Central configuration holder.
    نگهدارنده مرکزی تنظیمات.
    اولویت: Environment Variable > مقدار پیش‌فرض.
    """

    grpc_host: str = DEFAULT_GRPC_HOST
    grpc_port: int = DEFAULT_GRPC_PORT
    doctor_timeout: float = DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS
    engine_retries: int = ENGINE_CONNECT_MAX_RETRIES
    engine_retry_delay: float = ENGINE_CONNECT_RETRY_DELAY
    failover_interval: float = FAILOVER_CHECK_INTERVAL_SECONDS
    default_interface: str = "tun0"
    log_level: int = logging.WARNING

    @property
    def grpc_endpoint(self) -> str:
        return f"http://{self.grpc_host}:{self.grpc_port}"

    @classmethod
    def from_env(cls) -> AppConfig:
        """Build config from environment variables when present.
        تنظیمات را از متغیرهای محیطی می‌سازد (در صورت وجود).
        در برابر مقادیر نامعتبر مقاوم است.
        """

        def _get_int(name: str, default: int) -> int:
            val = os.getenv(name)
            if val is None:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        def _get_float(name: str, default: float) -> float:
            val = os.getenv(name)
            if val is None:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        log_level_raw = os.getenv("BIMARZ_LOG_LEVEL", "").upper()
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = log_level_map.get(log_level_raw, logging.WARNING)

        return cls(
            grpc_host=os.getenv("BIMARZ_GRPC_HOST", DEFAULT_GRPC_HOST),
            grpc_port=_get_int("BIMARZ_GRPC_PORT", DEFAULT_GRPC_PORT),
            doctor_timeout=_get_float("BIMARZ_DOCTOR_TIMEOUT", DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS),
            engine_retries=_get_int("BIMARZ_ENGINE_RETRIES", ENGINE_CONNECT_MAX_RETRIES),
            engine_retry_delay=_get_float("BIMARZ_ENGINE_RETRY_DELAY", ENGINE_CONNECT_RETRY_DELAY),
            failover_interval=_get_float("BIMARZ_FAILOVER_INTERVAL", FAILOVER_CHECK_INTERVAL_SECONDS),
            default_interface=os.getenv("BIMARZ_DEFAULT_INTERFACE", "tun0"),
            log_level=log_level,
        )
