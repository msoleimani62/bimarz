"""
High-level connection orchestrator (context manager).
orchestrator سطح بالای اتصال (context manager).
"""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from typing import Any, cast

from bimarz.config import AppConfig
from bimarz.events import ConnectionEvent, EventHandler, EventPayload
from bimarz.failover import check_profile_health
from bimarz.helpers import profiles_by_id
from bimarz.models import ServerProfile
from bimarz.services.engine import EngineService
from bimarz.services.failover import FailoverService
from bimarz.services.killswitch import KillSwitchService
from bimarz.services.process import ProcessService
from bimarz.xray_manager import XrayProcess

logger = logging.getLogger(__name__)


class ConnectionService:
    """High-level connection orchestrator.
    orchestrator سطح بالای اتصال.
    فقط __aexit__ مسئول cleanup و انتشار ERROR است.
    """

    def __init__(
        self,
        config: AppConfig,
        process_svc: ProcessService | None = None,
        engine_svc: EngineService | None = None,
        ks_svc: KillSwitchService | None = None,
        event_handler: EventHandler | None = None,
    ) -> None:
        self.config = config
        self.process_svc = process_svc or ProcessService()
        self.engine_svc = engine_svc or EngineService(config)
        self.ks_svc = ks_svc or KillSwitchService()
        self._event_handler = event_handler
        self._stop_event = asyncio.Event()
        self._cleaned = False
        self._signals_registered: list[signal.Signals] = []

    def _emit(self, event: ConnectionEvent, **data: Any) -> None:
        payload = cast(EventPayload, data)
        if self._event_handler:
            self._event_handler(event, payload)
        logger.debug("Event %s: %s", event.name, data)

    async def __aenter__(self) -> ConnectionService:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Only __aexit__ is responsible for emitting ERROR
        # فقط __aexit__ مسئول انتشار ERROR است
        if exc is not None and not isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
            self._emit(ConnectionEvent.ERROR, error=str(exc))
        await self.cleanup()

    def _register_signals(self) -> None:
        """Register SIGTERM/SIGHUP handlers to trigger graceful stop.
        هندلرهای SIGTERM/SIGHUP را برای توقف نرم ثبت می‌کند.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGHUP):
            self._try_register_signal(loop, sig)

    def _try_register_signal(self, loop: asyncio.AbstractEventLoop, sig: signal.Signals) -> None:
        try:
            loop.add_signal_handler(sig, self._stop_event.set)
            self._signals_registered.append(sig)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug("Signal handler unavailable for %s: %s", sig, exc)

    def _unregister_signals(self) -> None:
        """Remove previously registered signal handlers.
        هندلرهای سیگنال ثبت‌شده را حذف می‌کند.
        """
        loop = asyncio.get_running_loop()
        for sig in self._signals_registered:
            with suppress(NotImplementedError, RuntimeError, ValueError):
                loop.remove_signal_handler(sig)
        self._signals_registered.clear()

    async def start(
        self,
        profile: ServerProfile,
        *,
        auto_failover: bool = False,
        killswitch: bool = False,
        all_profiles: list[ServerProfile] | None = None,
    ) -> None:
        """Start connection and monitoring.
        Cleanup and ERROR emission are owned exclusively by __aexit__.
        اتصال و نظارت را شروع می‌کند.
        cleanup و انتشار ERROR منحصراً توسط __aexit__ انجام می‌شود.
        """
        self._emit(ConnectionEvent.STARTED, profile_id=profile.profile_id)

        proc = self.process_svc.start(profile)
        await self.engine_svc.connect()
        await self.engine_svc.add_outbound(profile)
        self._emit(ConnectionEvent.ENGINE_READY)

        if killswitch:
            self.ks_svc.enable(interface=self.config.default_interface)
            self._emit(ConnectionEvent.KILLSWITCH_ENABLED)

        self._register_signals()

        if auto_failover and all_profiles:
            await self._failover_loop(profile, all_profiles, proc)
        else:
            await self._watch_loop(proc)

    async def _failover_loop(
        self,
        initial: ServerProfile,
        all_profiles: list[ServerProfile],
        proc: XrayProcess,
    ) -> None:
        """Monitor health and perform automatic failover when needed.
        سلامت را نظارت کرده و در صورت نیاز failover خودکار انجام می‌دهد.
        """
        failover = FailoverService(initial.profile_id)
        profile_map = profiles_by_id(all_profiles)
        active = initial

        while not self._stop_event.is_set() and proc.is_running():
            if failover.active_id in profile_map:
                active = profile_map[failover.active_id]

            health = await check_profile_health(active)
            failover.record(health)

            if failover.should_trigger():
                best = failover.pick_best(list(profile_map.values()))
                if best is None:
                    logger.error("No alternative profile available")
                    break

                await self.engine_svc.remove_outbound()
                await self.engine_svc.add_outbound(best)
                failover.trigger(best.profile_id)
                active = best
                self._emit(ConnectionEvent.FAILOVER_TRIGGERED, new_profile_id=best.profile_id)

            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(ConnectionEvent.KILLSWITCH_WATCHER_DIED)
                break

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.failover_interval,
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _watch_loop(self, proc: XrayProcess) -> None:
        """Simple watch loop without failover.
        حلقه نظارت ساده بدون failover.
        """
        while not self._stop_event.is_set() and proc.is_running():
            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(ConnectionEvent.KILLSWITCH_WATCHER_DIED)
                break
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=1.0)
                break
            except asyncio.TimeoutError:
                continue

    async def cleanup(self) -> None:
        """Idempotent cleanup.
        پاک‌سازی idempotent.
        """
        if self._cleaned:
            return
        self._cleaned = True

        self._unregister_signals()
        self.process_svc.stop()
        self._emit(ConnectionEvent.PROCESS_STOPPED)

        if self.ks_svc.is_active():
            self.ks_svc.disable()

        self._emit(ConnectionEvent.CLEANUP_DONE)

    def request_stop(self) -> None:
        self._stop_event.set()
