"""
gRPC engine connection service.
سرویس اتصال به موتور gRPC.
"""

from __future__ import annotations

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
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._engine: EngineClient | None = None

    async def connect(self) -> EngineClient:
        """Connect to the gRPC engine with retries.
        با تلاش مجدد به موتور gRPC متصل می‌شود.
        """
        engine_class = get_engine_client_class()
        engine = await connect_with_retry(
            engine_class,
            max_retries=self.config.engine_retries,
            delay=self.config.engine_retry_delay,
        )
        self._engine = engine
        return engine

    def add_outbound(self, profile: ServerProfile) -> None:
        """Add VLESS Reality outbound for the given profile.
        outbound از نوع VLESS Reality را برای پروفایل اضافه می‌کند.
        """
        if self._engine is None:
            raise RuntimeError("Engine not connected")
        self._engine.add_vless_reality_outbound(**outbound_kwargs(profile))

    def remove_outbound(self, tag: str = ACTIVE_OUTBOUND_TAG) -> None:
        """Remove outbound by tag (best-effort).
        outbound را بر اساس تگ حذف می‌کند (بهترین تلاش).
        """
        if self._engine is None:
            return
        try:
            self._engine.remove_outbound(tag)
        except Exception as exc:
            logger.warning("remove_outbound failed: %s", exc)

    @property
    def engine(self) -> EngineClient | None:
        return self._engine
