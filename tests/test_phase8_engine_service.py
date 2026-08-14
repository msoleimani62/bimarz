"""
Phase 8 engine ownership tests.

Tests explicit engine client ownership and release semantics.

تست‌های مالکیت engine در فاز ۸.

مالکیت صریح کلاینت engine و رفتار آزادسازی آن را بررسی می‌کند.
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
    """close() must be safe when no client is owned."""
    service = EngineService(AppConfig())

    await service.close()

    assert service.engine is None


@pytest.mark.asyncio
async def test_engine_service_close_clears_reference_on_failure() -> None:
    """Ownership must be released even when client close fails."""
    client = MagicMock()
    client.close = AsyncMock(side_effect=RuntimeError("close failed"))

    service = EngineService(AppConfig())
    service._engine = client

    with pytest.raises(RuntimeError, match="close failed"):
        await service.close()

    assert service.engine is None


@pytest.mark.asyncio
async def test_engine_service_remove_can_propagate_failure() -> None:
    """Outbound removal failures must remain observable."""
    client = MagicMock()
    client.remove_outbound = AsyncMock(
        side_effect=RuntimeError("remove failed"),
    )

    service = EngineService(AppConfig())
    service._engine = client

    with pytest.raises(RuntimeError, match="remove failed"):
        await service.remove_outbound(raise_on_error=True)


@pytest.mark.asyncio
async def test_engine_service_add_uses_canonical_outbound_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outbound creation must always use the canonical active tag."""
    client = MagicMock()
    client.add_vless_reality_outbound = AsyncMock()

    service = EngineService(AppConfig())
    service._engine = client

    profile = MagicMock()
    profile.outbound_config = {
        "address": "example.com",
        "port": 443,
    }

    monkeypatch.setattr(
        "bimarz.services.engine.outbound_kwargs",
        lambda _profile: {
            "tag": "wrong-tag",
            "address": "example.com",
            "port": 443,
        },
    )

    await service.add_outbound(profile)

    kwargs = client.add_vless_reality_outbound.await_args.kwargs

    assert kwargs["tag"] == "bimarz-active"
