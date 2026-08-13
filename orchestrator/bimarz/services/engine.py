"""
gRPC engine connection service.

سرویس اتصال به موتور gRPC.
"""

from __future__ import annotations

import inspect
import logging

from bimarz.config import AppConfig
from bimarz.constants import ACTIVE_OUTBOUND_TAG
from bimarz.engine import get_engine_client_class
from bimarz.helpers import outbound_kwargs
from bimarz.models import ServerProfile
from bimarz.protocols import EngineClient
from bimarz.utils.retry import connect_with_retry

logger = logging.getLogger(__name__)


class EngineService:
    """Own the lifecycle of the gRPC engine client.

    چرخه عمر کلاینت gRPC موتور را مدیریت می‌کند.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._engine: EngineClient | None = None

    async def connect(self) -> EngineClient:
        """Connect to the gRPC engine with retries.

        با تلاش مجدد به موتور gRPC متصل می‌شود.
        """
        if self._engine is not None:
            return self._engine

        engine_class = get_engine_client_class()
        engine = await connect_with_retry(
            engine_class,
            endpoint=self.config.grpc_endpoint,
            max_retries=self.config.engine_retries,
            delay=self.config.engine_retry_delay,
        )
        self._engine = engine
        return engine

    async def add_outbound(self, profile: ServerProfile) -> None:
        """Add the VLESS Reality outbound for a profile.

        outbound از نوع VLESS Reality را برای پروفایل اضافه می‌کند.
        """
        if self._engine is None:
            raise RuntimeError("Engine not connected")

        await self._engine.add_vless_reality_outbound(**outbound_kwargs(profile))

    async def remove_outbound(
        self,
        tag: str = ACTIVE_OUTBOUND_TAG,
        *,
        raise_on_error: bool = False,
    ) -> None:
        """Remove an outbound and optionally propagate failures.

        outbound را حذف می‌کند و در صورت درخواست، خطا را propagate می‌کند.
        """
        if self._engine is None:
            return

        try:
            await self._engine.remove_outbound(tag)
        except Exception as exc:
            logger.warning("remove_outbound failed for %s: %s", tag, exc)
            if raise_on_error:
                raise

    async def close(self) -> None:
        """Release ownership of the engine client.

        مالکیت کلاینت engine را به‌صورت صریح آزاد می‌کند.
        """
        engine = self._engine
        self._engine = None

        if engine is None:
            return

        close = getattr(engine, "close", None)
        if not callable(close):
            return

        try:
            result = close()
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Engine client close failed")
            raise

    @property
    def engine(self) -> EngineClient | None:
        """Return the currently owned engine client.

        کلاینت engine تحت مالکیت سرویس را برمی‌گرداند.
        """
        return self._engine
