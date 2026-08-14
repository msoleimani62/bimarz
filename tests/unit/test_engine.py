"""
Unit tests for the high-level engine service.

تست‌های واحد سرویس سطح بالای موتور.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from bimarz.config import AppConfig
from bimarz.engine import EngineNotBuiltError
from bimarz.models import ServerProfile
from bimarz.services.engine import EngineService


def _profile() -> ServerProfile:
    return ServerProfile(
        profile_id="p1",
        tag="p1",
        remark="Test",
        outbound_config={
            "id": "11111111-1111-4111-8111-111111111111",
            "address": "example.com",
            "port": 443,
            "flow": "xtls-rprx-vision",
            "type": "tcp",
            "sni": "example.com",
            "fp": "chrome",
            "publicKey": "abc",
            "shortId": "a1",
            "spiderX": "/",
        },
        added_at_iso="2026-08-08T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_connect_propagates_engine_not_built_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EngineService(AppConfig())
    error = EngineNotBuiltError("Rust extension is not built")

    def raise_error() -> type:
        raise error

    monkeypatch.setattr(
        "bimarz.services.engine.get_engine_client_class",
        raise_error,
    )

    with pytest.raises(EngineNotBuiltError, match="Rust extension is not built"):
        await service.connect()


@pytest.mark.asyncio
async def test_connect_uses_retry_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EngineService(
        AppConfig(
            grpc_host="127.0.0.1",
            grpc_port=10085,
            engine_retries=3,
            engine_retry_delay=0.25,
        )
    )

    client = AsyncMock()
    engine_class = object
    retry = AsyncMock(return_value=client)

    monkeypatch.setattr(
        "bimarz.services.engine.get_engine_client_class",
        lambda: engine_class,
    )
    monkeypatch.setattr(
        "bimarz.services.engine.connect_with_retry",
        retry,
    )

    result = await service.connect()

    assert result is client
    assert service.engine is client
    retry.assert_awaited_once_with(
        engine_class,
        endpoint="http://127.0.0.1:10085",
        max_retries=3,
        delay=0.25,
    )


@pytest.mark.asyncio
async def test_add_outbound_requires_connection() -> None:
    service = EngineService(AppConfig())

    with pytest.raises(RuntimeError, match="not connected"):
        await service.add_outbound(_profile())


@pytest.mark.asyncio
async def test_add_outbound_delegates_to_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncMock()
    service = EngineService(AppConfig())
    service._engine = client

    monkeypatch.setattr(
        "bimarz.services.engine.outbound_kwargs",
        lambda profile: {
            "tag": profile.tag,
            "address": "example.com",
            "port": 443,
        },
    )

    await service.add_outbound(_profile())

    client.add_vless_reality_outbound.assert_awaited_once_with(
        tag="bimarz-active",
        address="example.com",
        port=443,
    )


@pytest.mark.asyncio
async def test_add_outbound_propagates_engine_error() -> None:
    client = AsyncMock()
    client.add_vless_reality_outbound.side_effect = RuntimeError("grpc failure")

    service = EngineService(AppConfig())
    service._engine = client

    with pytest.raises(RuntimeError, match="grpc failure"):
        await service.add_outbound(_profile())


@pytest.mark.asyncio
async def test_remove_outbound_does_not_fail_when_engine_is_missing() -> None:
    service = EngineService(AppConfig())

    result = await service.remove_outbound("missing")

    assert result is None


@pytest.mark.asyncio
async def test_remove_outbound_delegates_to_engine() -> None:
    client = AsyncMock()
    service = EngineService(AppConfig())
    service._engine = client

    await service.remove_outbound("test-tag")

    client.remove_outbound.assert_awaited_once_with("test-tag")


@pytest.mark.asyncio
async def test_remove_outbound_suppresses_engine_error() -> None:
    client = AsyncMock()
    client.remove_outbound.side_effect = RuntimeError("grpc failure")

    service = EngineService(AppConfig())
    service._engine = client

    await service.remove_outbound("test-tag")

    client.remove_outbound.assert_awaited_once_with("test-tag")
