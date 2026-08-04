"""
Generic retry helper for connecting to the gRPC engine.
کمک‌تابع عمومی برای تلاش مجدد در اتصال به موتور gRPC.
"""

from __future__ import annotations

import asyncio
import logging

from bimarz.constants import ENGINE_CONNECT_MAX_RETRIES, ENGINE_CONNECT_RETRY_DELAY
from bimarz.protocols import EngineClient

logger = logging.getLogger(__name__)


def is_retryable(exc: Exception) -> bool:
    """Return True if the exception is considered transient and retryable.
    اگر استثنا موقتی و قابل تلاش مجدد باشد True برمی‌گرداند.
    """
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    try:
        import grpc  # type: ignore

        if isinstance(exc, grpc.RpcError):
            code = exc.code()
            return code in (
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                grpc.StatusCode.RESOURCE_EXHAUSTED,
            )
    except ImportError:
        pass
    return False


async def connect_with_retry(
    engine_client_class: type,
    endpoint: str,
    max_retries: int = ENGINE_CONNECT_MAX_RETRIES,
    delay: float = ENGINE_CONNECT_RETRY_DELAY,
) -> EngineClient:
    """Connect to the engine with retries.
    با تلاش مجدد به موتور متصل می‌شود.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await engine_client_class.connect(endpoint)
        except Exception as exc:
            if is_retryable(exc):
                last_exc = exc
                logger.debug("Engine connect attempt %d/%d failed: %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to connect to engine after retries")
