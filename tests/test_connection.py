"""
Tests for the high-level ConnectionService.

تست‌های سرویس سطح بالای اتصال.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from bimarz.config import AppConfig
from bimarz.connection import ConnectionService
from bimarz.events import ConnectionEvent
from bimarz.models import ServerProfile


def _profile(profile_id: str = "p1") -> ServerProfile:
    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark=f"Profile {profile_id}",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-08-08T00:00:00+00:00",
    )


def _process(running: bool = False) -> MagicMock:
    proc = MagicMock()
    proc.is_running.return_value = running
    return proc


def test_context_manager_cleanup_is_idempotent() -> None:
    process = MagicMock()
    process.stop = MagicMock()

    engine = MagicMock()
    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append((event, data)),
        )

        async with conn:
            pass

        await conn.cleanup()

    asyncio.run(run())

    process.stop.assert_called_once()
    assert [event for event, _ in events] == [
        ConnectionEvent.PROCESS_STOPPED,
        ConnectionEvent.CLEANUP_DONE,
    ]


def test_cleanup_disables_active_killswitch() -> None:
    process = MagicMock()
    killswitch = MagicMock()
    killswitch.is_active.return_value = True

    conn = ConnectionService(
        AppConfig(),
        process_svc=process,
        engine_svc=MagicMock(),
        ks_svc=killswitch,
    )

    asyncio.run(conn.cleanup())

    process.stop.assert_called_once()
    killswitch.disable.assert_called_once()


def test_request_stop_sets_stop_event() -> None:
    conn = ConnectionService(
        AppConfig(),
        process_svc=MagicMock(),
        engine_svc=MagicMock(),
        ks_svc=MagicMock(),
    )

    assert conn._stop_event.is_set() is False
    conn.request_stop()
    assert conn._stop_event.is_set() is True


def test_emit_calls_handler() -> None:
    events = []
    conn = ConnectionService(
        AppConfig(),
        process_svc=MagicMock(),
        engine_svc=MagicMock(),
        ks_svc=MagicMock(),
        event_handler=lambda event, data: events.append((event, data)),
    )

    conn._emit(ConnectionEvent.STARTED, profile_id="p1")

    assert events == [(ConnectionEvent.STARTED, {"profile_id": "p1"})]


def test_start_without_failover_runs_watch_loop() -> None:
    process = MagicMock()
    process.start.return_value = _process(False)

    engine = MagicMock()
    engine.connect = AsyncMock()
    engine.add_outbound = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(event),
        )
        await conn.start(_profile())

    asyncio.run(run())

    process.start.assert_called_once()
    engine.connect.assert_awaited_once()
    engine.add_outbound.assert_awaited_once()
    assert ConnectionEvent.STARTED in events
    assert ConnectionEvent.ENGINE_READY in events


def test_start_enables_killswitch() -> None:
    process = MagicMock()
    process.start.return_value = _process(False)

    engine = MagicMock()
    engine.connect = AsyncMock()
    engine.add_outbound = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(default_interface="tun9"),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(event),
        )
        await conn.start(_profile(), killswitch=True)

    asyncio.run(run())

    killswitch.enable.assert_called_once_with(interface="tun9")
    assert ConnectionEvent.KILLSWITCH_ENABLED in events


def test_watch_loop_stops_when_killswitch_watcher_dies() -> None:
    process = _process(True)
    killswitch = MagicMock()
    killswitch.is_active.return_value = True
    killswitch.is_watcher_alive.return_value = False

    events = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=MagicMock(),
            engine_svc=MagicMock(),
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(event),
        )
        await conn._watch_loop(process)

    asyncio.run(run())

    assert ConnectionEvent.KILLSWITCH_WATCHER_DIED in events


def test_aexit_emits_error_and_cleans_up() -> None:
    events = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=MagicMock(),
            engine_svc=MagicMock(),
            ks_svc=MagicMock(),
            event_handler=lambda event, data: events.append((event, data)),
        )
        await conn.__aexit__(ValueError, ValueError("boom"), None)

    asyncio.run(run())

    assert events[0] == (ConnectionEvent.ERROR, {"error": "boom"})
    assert events[-1][0] == ConnectionEvent.CLEANUP_DONE


def test_signal_registration_failure_is_ignored() -> None:
    conn = ConnectionService(
        AppConfig(),
        process_svc=MagicMock(),
        engine_svc=MagicMock(),
        ks_svc=MagicMock(),
    )

    loop = MagicMock()
    loop.add_signal_handler.side_effect = RuntimeError("unsupported")

    conn._try_register_signal(loop, __import__("signal").SIGTERM)

    assert conn._signals_registered == []


def test_unregister_signals_clears_registered_signals() -> None:
    conn = ConnectionService(
        AppConfig(),
        process_svc=MagicMock(),
        engine_svc=MagicMock(),
        ks_svc=MagicMock(),
    )

    conn._signals_registered = [__import__("signal").SIGTERM]

    loop = MagicMock()
    original = asyncio.get_running_loop

    async def run() -> None:
        import bimarz.connection as module

        module.asyncio.get_running_loop = lambda: loop
        try:
            conn._unregister_signals()
        finally:
            module.asyncio.get_running_loop = original

    asyncio.run(run())

    loop.remove_signal_handler.assert_called_once()
    assert conn._signals_registered == []
