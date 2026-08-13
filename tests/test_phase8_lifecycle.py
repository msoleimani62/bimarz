"""
Phase 8 lifecycle reliability tests.

Validates partial-failure rollback, cleanup observability, idempotency,
failover exhaustion, and resource ownership without requiring the native
extension or a live Xray binary.

تست‌های قابلیت اطمینان چرخه عمر فاز ۸.

rollback در شکست جزئی، observability در cleanup، idempotency،
خستگی failover و مالکیت منابع را بدون نیاز به extension native
یا باینری زنده Xray اعتبارسنجی می‌کند.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bimarz.config import AppConfig
from bimarz.connection import ConnectionService
from bimarz.events import ConnectionEvent
from bimarz.models import HealthCheckResult, ServerProfile
from bimarz.services.engine import EngineService
from bimarz.services.failover import FailoverService


def _profile(profile_id: str = "p1") -> ServerProfile:
    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark=f"Profile {profile_id}",
        outbound_config={
            "address": "example.com",
            "port": 443,
        },
        added_at_iso="2026-08-08T00:00:00+00:00",
    )


def _process(running: bool = False) -> MagicMock:
    proc = MagicMock()
    proc.is_running.return_value = running
    return proc


def _health(
    profile_id: str,
    reachable: bool,
    latency_ms: float | None = None,
) -> HealthCheckResult:
    return HealthCheckResult(
        profile_id=profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso="2026-08-12T00:00:00+00:00",
        error_message=None if reachable else "unreachable",
    )


def test_start_rolls_back_process_when_engine_connect_fails() -> None:
    """Process must not remain owned after engine connect failure.
    پس از شکست اتصال engine نباید مالکیت process باقی بماند.
    """
    process = MagicMock()
    process.start.return_value = _process(True)

    engine = MagicMock()
    engine.connect = AsyncMock(side_effect=ConnectionError("engine down"))
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events: list[ConnectionEvent] = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, _data: events.append(event),
        )

        with pytest.raises(ConnectionError, match="engine down"):
            await conn.start(_profile())

    asyncio.run(run())

    process.start.assert_called_once()
    process.stop.assert_called_once()
    engine.close.assert_awaited()
    killswitch.enable.assert_not_called()
    assert ConnectionEvent.STARTED in events
    assert ConnectionEvent.ENGINE_READY not in events


def test_start_rolls_back_when_add_outbound_fails() -> None:
    """Outbound failure after process start must stop the process.
    شکست outbound پس از start باید process را متوقف کند.
    """
    process = MagicMock()
    process.start.return_value = _process(True)

    engine = MagicMock()
    engine.connect = AsyncMock()
    engine.add_outbound = AsyncMock(
        side_effect=RuntimeError("bad outbound"),
    )
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
        )

        with pytest.raises(RuntimeError, match="bad outbound"):
            await conn.start(_profile())

    asyncio.run(run())

    process.stop.assert_called_once()
    engine.close.assert_awaited()


def test_start_rolls_back_killswitch_when_watcher_setup_raises() -> None:
    """Kill-switch enable followed by watcher failure must disable KS.
    فعال‌سازی kill-switch و سپس شکست watcher باید KS را غیرفعال کند.
    """
    process = MagicMock()
    process.start.return_value = _process(False)

    engine = MagicMock()
    engine.connect = AsyncMock()
    engine.add_outbound = AsyncMock()
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = True
    killswitch.start_watcher.side_effect = RuntimeError(
        "watcher failed",
    )

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(default_interface="tun9"),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
        )

        with pytest.raises(RuntimeError, match="watcher failed"):
            await conn.start(_profile(), killswitch=True)

    asyncio.run(run())

    killswitch.enable.assert_called_once_with(interface="tun9")
    killswitch.stop_watcher.assert_called_once()
    killswitch.disable.assert_called_once()
    process.stop.assert_called_once()


def test_cleanup_emits_error_when_killswitch_disable_fails() -> None:
    """Failed kill-switch disable must be observable, not silent success.
    شکست غیرفعال‌سازی kill-switch باید قابل مشاهده باشد، نه موفقیت خاموش.
    """
    process = MagicMock()
    engine = MagicMock()
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = True
    killswitch.disable.side_effect = RuntimeError("nft denied")

    events: list[tuple[ConnectionEvent, dict]] = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(
                (event, dict(data)),
            ),
        )

        conn._killswitch_enabled = True
        await conn.cleanup()

    asyncio.run(run())

    event_names = [event for event, _ in events]

    assert ConnectionEvent.PROCESS_STOPPED in event_names
    assert ConnectionEvent.ERROR in event_names
    assert ConnectionEvent.CLEANUP_DONE in event_names

    error_payloads = [data for event, data in events if event == ConnectionEvent.ERROR]

    assert error_payloads
    assert "kill-switch disable failed" in error_payloads[0].get(
        "error",
        "",
    )


def test_cleanup_is_idempotent_and_closes_engine_once() -> None:
    """Repeated cleanup must not re-stop resources.
    cleanup تکراری نباید منابع را دوباره متوقف کند.
    """
    process = MagicMock()
    engine = MagicMock()
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
        )

        await conn.cleanup()
        await conn.cleanup()
        await conn.cleanup()

    asyncio.run(run())

    process.stop.assert_called_once()
    engine.close.assert_awaited_once()


def test_context_manager_cleans_up_after_start_failure() -> None:
    """async with must cleanup even when start raises.
    حتی وقتی start خطا بدهد، async with باید cleanup کند.
    """
    process = MagicMock()
    process.start.side_effect = RuntimeError("no binary")

    engine = MagicMock()
    engine.close = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events: list[ConnectionEvent] = []

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=process,
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, _data: events.append(event),
        )

        with pytest.raises(RuntimeError, match="no binary"):
            async with conn:
                await conn.start(_profile())

    asyncio.run(run())

    assert ConnectionEvent.ERROR in events
    assert ConnectionEvent.CLEANUP_DONE in events
    process.stop.assert_called_once()


def test_failover_exhaustion_emits_error_and_stops_loop() -> None:
    """When no alternative exists, failover must error and exit the loop.
    وقتی جایگزینی نباشد، failover باید خطا بدهد و از حلقه خارج شود.
    """
    process = _process(True)
    process.is_running.side_effect = [True, False]

    engine = MagicMock()
    engine.remove_outbound = AsyncMock()
    engine.add_outbound = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events: list[tuple[ConnectionEvent, dict]] = []
    profiles = [
        _profile("p1"),
        _profile("p2"),
    ]

    async def fake_check(
        _all_profiles: list[ServerProfile],
    ) -> dict[str, HealthCheckResult]:
        return {
            "p1": _health("p1", False),
            "p2": _health("p2", False),
        }

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(failover_interval=0.01),
            process_svc=MagicMock(),
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(
                (event, dict(data)),
            ),
        )

        with (
            patch(
                "bimarz.connection.FailoverService",
                lambda initial: FailoverService(
                    initial,
                    consecutive_failure_threshold=1,
                ),
            ),
            patch(
                "bimarz.connection.check_all_profiles",
                fake_check,
            ),
        ):
            await conn._failover_loop(
                _profile("p1"),
                profiles,
                process,
            )

    asyncio.run(run())

    error_events = [data for event, data in events if event == ConnectionEvent.ERROR]

    assert error_events
    assert "no reachable alternative" in error_events[0]["error"]
    engine.remove_outbound.assert_not_called()
    engine.add_outbound.assert_not_called()


def test_failover_success_switches_outbound_once() -> None:
    """Successful failover must replace outbound exactly once per trigger.
    failover موفق باید outbound را دقیقاً یک‌بار در هر trigger عوض کند.
    """
    process = _process(True)
    process.is_running.side_effect = [True, False]

    engine = MagicMock()
    engine.remove_outbound = AsyncMock()
    engine.add_outbound = AsyncMock()

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    events: list[tuple[ConnectionEvent, dict]] = []
    profiles = [
        _profile("p1"),
        _profile("p2"),
    ]

    async def fake_check(
        _all_profiles: list[ServerProfile],
    ) -> dict[str, HealthCheckResult]:
        return {
            "p1": _health("p1", False),
            "p2": _health("p2", True, 40.0),
        }

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(failover_interval=0.01),
            process_svc=MagicMock(),
            engine_svc=engine,
            ks_svc=killswitch,
            event_handler=lambda event, data: events.append(
                (event, dict(data)),
            ),
        )

        with (
            patch(
                "bimarz.connection.FailoverService",
                lambda initial: FailoverService(
                    initial,
                    consecutive_failure_threshold=1,
                ),
            ),
            patch(
                "bimarz.connection.check_all_profiles",
                fake_check,
            ),
        ):
            await conn._failover_loop(
                _profile("p1"),
                profiles,
                process,
            )

    asyncio.run(run())

    engine.remove_outbound.assert_awaited_once()
    engine.add_outbound.assert_awaited_once()

    failover_events = [data for event, data in events if event == ConnectionEvent.FAILOVER_TRIGGERED]

    assert failover_events
    assert failover_events[0]["new_profile_id"] == "p2"
    assert failover_events[0]["old_profile_id"] == "p1"


def test_request_stop_ends_watch_loop() -> None:
    """request_stop must terminate an active watch loop.
    request_stop باید حلقه watch فعال را خاتمه دهد.
    """
    process = _process(True)

    killswitch = MagicMock()
    killswitch.is_active.return_value = False

    async def run() -> None:
        conn = ConnectionService(
            AppConfig(),
            process_svc=MagicMock(),
            engine_svc=MagicMock(),
            ks_svc=killswitch,
        )

        async def stop_soon() -> None:
            await asyncio.sleep(0.05)
            conn.request_stop()

        stopper = asyncio.create_task(stop_soon())

        await conn._watch_loop(process)
        await stopper

    asyncio.run(run())


def test_engine_service_close_is_idempotent() -> None:
    """EngineService.close must tolerate repeated calls.
    EngineService.close باید فراخوانی تکراری را تحمل کند.
    """
    engine = MagicMock()
    engine.close = AsyncMock()

    service = EngineService(AppConfig())
    service._engine = engine

    async def run() -> None:
        await service.close()
        await service.close()

    asyncio.run(run())

    engine.close.assert_awaited_once()
    assert service.engine is None


def test_failover_service_bounded_threshold() -> None:
    """Failover trigger remains bounded by consecutive failure threshold.
    فعال‌سازی failover با آستانه شکست متوالی محدود می‌ماند.
    """
    service = FailoverService(initial_profile_id="p1")
    threshold = service.manager.threshold

    for _ in range(threshold - 1):
        service.record(_health("p1", False))
        assert service.should_trigger() is False

    service.record(_health("p1", False))
    assert service.should_trigger() is True

    service.trigger(
        "p2",
        reason="threshold reached",
    )

    assert service.active_id == "p2"
    assert service.should_trigger() is False
