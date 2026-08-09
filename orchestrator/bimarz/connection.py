"""
High-level connection orchestrator.

orchestrator سطح بالای اتصال.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from typing import Any, cast

from bimarz.config import AppConfig
from bimarz.events import ConnectionEvent, EventHandler, EventPayload
from bimarz.failover import check_all_profiles
from bimarz.helpers import profiles_by_id
from bimarz.models import ServerProfile
from bimarz.services.engine import EngineService
from bimarz.services.failover import FailoverService
from bimarz.services.killswitch import KillSwitchService
from bimarz.services.process import ProcessService
from bimarz.xray_manager import XrayProcess

logger = logging.getLogger(__name__)


class ConnectionService:
    """High-level connection lifecycle orchestrator.

    مدیریت چرخه کامل اتصال.
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

        if self._event_handler is not None:
            self._event_handler(event, payload)

        logger.debug("Event %s: %s", event.name, data)

    async def __aenter__(self) -> ConnectionService:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        if exc is not None and not isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
            self._emit(ConnectionEvent.ERROR, error=str(exc))

        await self.cleanup()

    def _register_signals(self) -> None:
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGHUP):
            self._try_register_signal(loop, sig)

    def _try_register_signal(
        self,
        loop: asyncio.AbstractEventLoop,
        sig: signal.Signals,
    ) -> None:
        try:
            loop.add_signal_handler(sig, self._stop_event.set)
            self._signals_registered.append(sig)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug(
                "Signal handler unavailable for %s: %s",
                sig,
                exc,
            )

    def _unregister_signals(self) -> None:
        loop = asyncio.get_running_loop()

        for sig in self._signals_registered:
            with suppress(
                NotImplementedError,
                RuntimeError,
                ValueError,
            ):
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
        self._emit(
            ConnectionEvent.STARTED,
            profile_id=profile.profile_id,
        )

        proc = self.process_svc.start(profile)

        await self.engine_svc.connect()
        await self.engine_svc.add_outbound(profile)

        self._emit(ConnectionEvent.ENGINE_READY)

        if killswitch:
            self.ks_svc.enable(
                interface=self.config.default_interface,
            )
            self._emit(ConnectionEvent.KILLSWITCH_ENABLED)

        self._register_signals()

        if auto_failover and all_profiles:
            await self._failover_loop(
                profile,
                all_profiles,
                proc,
            )
        else:
            await self._watch_loop(proc)

    async def _failover_loop(
        self,
        initial: ServerProfile,
        all_profiles: list[ServerProfile],
        proc: XrayProcess,
    ) -> None:
        failover = FailoverService(initial.profile_id)
        profile_map = profiles_by_id(all_profiles)

        if initial.profile_id not in profile_map:
            profile_map[initial.profile_id] = initial

        while not self._stop_event.is_set() and proc.is_running():
            profiles = list(profile_map.values())
            results = await check_all_profiles(profiles)

            active_id = failover.active_id
            active_result = results.get(active_id)

            if active_result is not None:
                failover.record(active_result)

            if failover.should_trigger():
                best_id = failover.pick_best(results)

                if best_id is None:
                    logger.error("Failover required but no reachable alternative profile exists")
                    self._emit(
                        ConnectionEvent.ERROR,
                        error="failover required but no reachable alternative exists",
                    )
                    break

                best_profile = profile_map[best_id]

                await self.engine_svc.remove_outbound()
                await self.engine_svc.add_outbound(best_profile)

                event = failover.trigger(
                    best_id,
                    reason=(f"{failover.manager.threshold} consecutive health-check failures"),
                )

                self._emit(
                    ConnectionEvent.FAILOVER_TRIGGERED,
                    old_profile_id=event.from_profile_id,
                    new_profile_id=event.to_profile_id,
                    reason=event.reason,
                )

            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(
                    ConnectionEvent.KILLSWITCH_WATCHER_DIED,
                )
                break

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.failover_interval,
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _watch_loop(
        self,
        proc: XrayProcess,
    ) -> None:
        while not self._stop_event.is_set() and proc.is_running():
            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(
                    ConnectionEvent.KILLSWITCH_WATCHER_DIED,
                )
                break

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=1.0,
                )
                break
            except asyncio.TimeoutError:
                continue

    async def cleanup(self) -> None:
        if self._cleaned:
            return

        self._cleaned = True

        self._unregister_signals()

        with suppress(Exception):
            self.process_svc.stop()

        self._emit(ConnectionEvent.PROCESS_STOPPED)

        if self.ks_svc.is_active():
            with suppress(Exception):
                self.ks_svc.disable()

        self._emit(ConnectionEvent.CLEANUP_DONE)

    def request_stop(self) -> None:
        self._stop_event.set()
