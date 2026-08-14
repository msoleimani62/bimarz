"""
gRPC engine connection service.

Provides explicit ownership and lifecycle management for the engine client.

سرویس اتصال gRPC موتور.

مالکیت و چرخه عمر کلاینت موتور را به‌صورت صریح مدیریت می‌کند.
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

    مدیریت چرخه عمر کلاینت gRPC موتور.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._engine: EngineClient | None = None

    async def connect(self) -> EngineClient:
        """Connect to the engine and acquire client ownership.

        اتصال به engine و به‌دست گرفتن مالکیت کلاینت.
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

        if engine is None:
            raise RuntimeError("Engine connection returned no client")

        self._engine = engine
        return engine

    async def add_outbound(self, profile: ServerProfile) -> None:
        """Create the canonical active outbound.

        ساخت outbound فعال با شناسه canonical.
        """
        if self._engine is None:
            raise RuntimeError("Engine not connected")

        kwargs = outbound_kwargs(profile)
        kwargs["tag"] = ACTIVE_OUTBOUND_TAG

        await self._engine.add_vless_reality_outbound(**kwargs)

    async def remove_outbound(
        self,
        tag: str = ACTIVE_OUTBOUND_TAG,
        *,
        raise_on_error: bool = False,
    ) -> None:
        """Remove an outbound and optionally propagate failures.

        حذف outbound و در صورت نیاز انتقال خطا به caller.
        """
        if self._engine is None:
            return

        try:
            await self._engine.remove_outbound(tag)
        except Exception as exc:
            logger.warning(
                "remove_outbound failed for %s: %s",
                tag,
                exc,
            )
            if raise_on_error:
                raise

    async def close(self) -> None:
        """Release engine ownership even when client close fails.

        آزادسازی مالکیت engine حتی در صورت شکست close.
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

        کلاینت engine تحت مالکیت فعلی سرویس.
        """
        return self._engine
