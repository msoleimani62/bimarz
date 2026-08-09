"""
Protocol definitions used for dependency injection across services.

تعاریف Protocol برای تزریق وابستگی بین سرویس‌ها.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

from bimarz.xray_manager import XrayProcess


class EngineClient(Protocol):
    """Protocol for the asynchronous gRPC engine client.

    پروتکل کلاینت asynchronous موتور gRPC.
    """

    @classmethod
    async def connect(cls, endpoint: str) -> EngineClient: ...

    async def add_vless_reality_outbound(
        self,
        **kwargs: Any,
    ) -> Any: ...

    async def remove_outbound(
        self,
        tag: str,
    ) -> Any: ...

    async def get_outbound_stats(
        self,
        tag: str,
    ) -> Any: ...

    async def close(self) -> Any: ...


class BinaryFinder(Protocol):
    """Protocol for locating the xray-core binary.

    پروتکل پیدا کردن باینری xray-core.
    """

    def __call__(self) -> Path | str | None: ...


class ConfigBuilder(Protocol):
    """Protocol for building xray configuration.

    پروتکل ساخت تنظیمات xray.
    """

    def __call__(
        self,
        grpc_endpoint: str = ...,
        local_socks_port: int = ...,
        enable_dns_guard: bool = ...,
    ) -> str: ...


class ProcessFactory(Protocol):
    """Protocol for creating an XrayProcess.

    پروتکل ساخت XrayProcess.
    """

    def __call__(
        self,
        binary: Path | str,
        config: Path,
    ) -> XrayProcess: ...


HealthCheckFunction = Callable[
    [str, int, int],
    Awaitable[tuple[bool, float | None, str | None]],
]

BatchHealthCheckFunction = Callable[
    [
        list[tuple[str, str, int]],
        int,
    ],
    Awaitable[
        list[
            tuple[
                str,
                bool,
                float | None,
                str | None,
            ]
        ]
    ],
]
