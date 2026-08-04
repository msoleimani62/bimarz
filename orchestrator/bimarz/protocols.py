"""
Protocol definitions used for dependency injection across services.
تعاریف Protocol که برای تزریق وابستگی در سرویس‌ها استفاده می‌شوند.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from bimarz.xray_manager import XrayProcess


class EngineClient(Protocol):
    """Protocol matching the gRPC engine client surface used by services.
    پروتکل مطابق با سطح کلاینت gRPC که در سرویس‌ها استفاده می‌شود.
    """
    def add_vless_reality_outbound(self, **kwargs: Any) -> None: ...
    def remove_outbound(self, tag: str) -> None: ...


class BinaryFinder(Protocol):
    """Protocol for locating the xray-core binary.
    پروتکل برای پیدا کردن باینری xray-core.
    """
    def __call__(self) -> Path | str | None: ...


class ConfigBuilder(Protocol):
    """Protocol matching the real signature of build_connect_config.
    پروتکل مطابق با امضای واقعی build_connect_config.
    """
    def __call__(
        self,
        grpc_endpoint: str = ...,
        local_socks_port: int = ...,
        enable_dns_guard: bool = ...,
    ) -> str: ...


class ProcessFactory(Protocol):
    """Protocol for creating an XrayProcess instance.
    پروتکل برای ساخت نمونه XrayProcess.
    """
    def __call__(self, binary: str, config_path: Path) -> XrayProcess: ...
