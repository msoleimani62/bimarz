"""
Phase 8 engine ownership tests.

تست‌های مالکیت engine در فاز ۸.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from bimarz.config import AppConfig
from bimarz.services.engine import EngineService


@pytest.mark.asyncio
async def test_engine_service_close_releases_client() -> None:
    """close() must release the owned engine client."""
    client = MagicMock()
    client.close = AsyncMock()

    service = EngineService(AppConfig())
    service._engine = client

    await service.close()

    client.close.assert_awaited_once()
    assert service.engine is None


@pytest.mark.asyncio
async def test_engine_service_close_is_safe_without_client() -> None:
    """close() must be idempotent when no client is owned."""
    service = EngineService(AppConfig())

    await service.close()

    assert service.engine is None


@pytest.mark.asyncio
async def test_engine_service_close_clears_reference_on_failure() -> None:
    """Client ownership must be released even when close fails."""
    client = MagicMock()
    client.close = AsyncMock(side_effect=RuntimeError("close failed"))

    service = EngineService(AppConfig())
    service._engine = client

    with pytest.raises(RuntimeError, match="close failed"):
        await service.close()

    assert service.engine is None


@pytest.mark.asyncio
async def test_engine_service_remove_can_propagate_failure() -> None:
    """Cleanup callers must be able to observe outbound removal failures."""
    client = MagicMock()
    client.remove_outbound = AsyncMock(
        side_effect=RuntimeError("remove failed"),
    )

    service = EngineService(AppConfig())
    service._engine = client

    with pytest.raises(RuntimeError, match="remove failed"):
        await service.remove_outbound(raise_on_error=True)
