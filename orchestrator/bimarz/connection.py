"""
High-level connection lifecycle orchestrator.

Orchestrates transactional startup, rollback, cleanup, failover, and
resource ownership for the application connection lifecycle.

مدیریت چرخه عمر اتصال در سطح بالا.

چرخه راه‌اندازی تراکنشی، rollback، cleanup، failover و مالکیت منابع را
برای چرخه عمر اتصال برنامه مدیریت می‌کند.
"""

from __future__ import annotations

import asyncio
import inspect
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
    """Manage the complete connection lifecycle.

    مدیریت کامل چرخه عمر اتصال.
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
        self._started = False
        self._process_owned = False
        self._engine_owned = False
        self._outbound_owned = False
        self._killswitch_enabled = False
        self._signals_registered: list[signal.Signals] = []

    def _emit(self, event: ConnectionEvent, **data: Any) -> None:
        payload = cast(EventPayload, data)

        if self._event_handler is not None:
            try:
                self._event_handler(event, payload)
            except Exception:
                # خطای observer نباید چرخه عمر را متوقف کند.
                # Observer failures must never abort the lifecycle.
                logger.exception("Connection event handler failed for %s", event.name)

        logger.debug("Event %s: %s", event.name, data)

    async def __aenter__(self) -> ConnectionService:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        if exc is not None and not isinstance(
            exc,
            (asyncio.CancelledError, KeyboardInterrupt),
        ):
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
        if not self._signals_registered:
            return

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
        self._stop_event.clear()
        self._cleaned = False
        self._started = False
        self._process_owned = False
        self._engine_owned = False
        self._outbound_owned = False
        self._killswitch_enabled = False

        self._emit(
            ConnectionEvent.STARTED,
            profile_id=profile.profile_id,
        )

        try:
            proc = self.process_svc.start(profile)
            self._process_owned = True

            await self.engine_svc.connect()
            self._engine_owned = True

            await self.engine_svc.add_outbound(profile)
            self._outbound_owned = True
            self._emit(ConnectionEvent.ENGINE_READY)

            if killswitch:
                self.ks_svc.enable(
                    interface=self.config.default_interface,
                )
                self._killswitch_enabled = True
                self._emit(ConnectionEvent.KILLSWITCH_ENABLED)

                self.ks_svc.start_watcher(
                    poll_fn=proc.is_running,
                )

            self._register_signals()

            self._started = True

            if auto_failover and all_profiles:
                await self._failover_loop(
                    profile,
                    all_profiles,
                    proc,
                )
            else:
                await self._watch_loop(proc)

        except BaseException as primary_error:
            rollback_errors = await self._rollback()

            if rollback_errors:
                self._emit(
                    ConnectionEvent.ERROR,
                    error=(
                        f"startup failed: {primary_error}; "
                        f"rollback failed: {'; '.join(rollback_errors)}"
                    ),
                )

            raise

    async def _rollback(self) -> list[str]:
        return await self._cleanup_resources(
            emit_cleanup_done=False,
            mark_cleaned=False,
        )

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
                    message = (
                        "failover required but no reachable alternative exists"
                    )
                    logger.error(message)
                    self._emit(
                        ConnectionEvent.ERROR,
                        error=message,
                    )
                    break

                best_profile = profile_map[best_id]

                try:
                    await self.engine_svc.remove_outbound(
                        raise_on_error=True,
                    )
                    self._outbound_owned = False

                    await self.engine_svc.add_outbound(best_profile)
                    self._outbound_owned = True
                except Exception as exc:
                    logger.exception(
                        "Failover switch failed; attempting outbound recovery"
                    )

                    recovery_error: Exception | None = None

                    try:
                        if self._outbound_owned:
                            await self.engine_svc.remove_outbound(
                                raise_on_error=True,
                            )
                            self._outbound_owned = False
                    except Exception as recovery_exc:
                        recovery_error = recovery_exc

                    try:
                        await self.engine_svc.add_outbound(
                            profile_map[active_id],
                        )
                        self._outbound_owned = True
                    except Exception as recovery_exc:
                        recovery_error = recovery_exc

                    message = f"failover switch failed: {exc}"
                    if recovery_error is not None:
                        message += f"; recovery failed: {recovery_error}"

                    self._emit(
                        ConnectionEvent.ERROR,
                        error=message,
                    )
                    break

                event = failover.trigger(
                    best_id,
                    reason=(
                        f"{failover.manager.threshold} consecutive "
                        "health-check failures"
                    ),
                )

                self._emit(
                    ConnectionEvent.FAILOVER_TRIGGERED,
                    old_profile_id=event.from_profile_id,
                    new_profile_id=event.to_profile_id,
                    reason=event.reason,
                )

                active_id = best_id

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

    async def _await_if_needed(self, result: object) -> object:
        if inspect.isawaitable(result):
            return await result
        return result

    async def _cleanup_resources(
        self,
        *,
        emit_cleanup_done: bool,
        mark_cleaned: bool,
    ) -> list[str]:
        errors: list[str] = []

        try:
            self._unregister_signals()
        except Exception as exc:
            message = f"signal cleanup failed: {exc}"
            logger.warning(message)
            errors.append(message)

        try:
            self.ks_svc.stop_watcher()
        except Exception as exc:
            message = f"kill-switch watcher stop failed: {exc}"
            logger.warning(message)
            errors.append(message)

        if self._outbound_owned:
            try:
                result = self.engine_svc.remove_outbound(
                    raise_on_error=True,
                )
                await self._await_if_needed(result)
            except Exception as exc:
                message = f"engine outbound cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)
            else:
                self._outbound_owned = False

        if self._engine_owned or self.engine_svc.engine is not None:
            try:
                result = self.engine_svc.close()
                await self._await_if_needed(result)
            except Exception as exc:
                message = f"engine client cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)
            finally:
                self._engine_owned = False

        if self._process_owned:
            try:
                self.process_svc.stop()
            except Exception as exc:
                message = f"xray process cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)
            else:
                self._process_owned = False
                self._emit(ConnectionEvent.PROCESS_STOPPED)

        if self._killswitch_enabled:
            try:
                self.ks_svc.disable()
            except Exception as exc:
                message = f"kill-switch disable failed: {exc}"
                logger.error(message)
                errors.append(message)
            else:
                self._killswitch_enabled = False

        self._started = False

        if mark_cleaned:
            self._cleaned = True

        if errors:
            logger.warning(
                "Connection cleanup completed with %d error(s): %s",
                len(errors),
                "; ".join(errors),
            )
            self._emit(
                ConnectionEvent.ERROR,
                error="; ".join(errors),
            )

        if emit_cleanup_done:
            self._emit(ConnectionEvent.CLEANUP_DONE)

        return errors

    async def cleanup(self) -> None:
        if self._cleaned:
            return

        errors: list[str] = []

        try:
            try:
                self._unregister_signals()
            except Exception as exc:
                message = f"signal cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)

            try:
                self.ks_svc.stop_watcher()
            except Exception as exc:
                message = f"kill-switch watcher stop failed: {exc}"
                logger.warning(message)
                errors.append(message)

            try:
                result = self.engine_svc.remove_outbound(
                    raise_on_error=True,
                )
                await self._await_if_needed(result)
            except Exception as exc:
                message = f"engine outbound cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)

            try:
                result = self.engine_svc.close()
                await self._await_if_needed(result)
            except Exception as exc:
                message = f"engine client cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)

            try:
                self.process_svc.stop()
            except Exception as exc:
                message = f"xray process cleanup failed: {exc}"
                logger.warning(message)
                errors.append(message)
            else:
                self._emit(ConnectionEvent.PROCESS_STOPPED)

            try:
                if self._killswitch_enabled:
                    self.ks_svc.disable()
                    self._killswitch_enabled = False
            except Exception as exc:
                message = f"kill-switch disable failed: {exc}"
                logger.error(message)
                errors.append(message)
        finally:
            self._cleaned = True

            if errors:
                self._emit(
                    ConnectionEvent.ERROR,
                    error="; ".join(errors),
                )
                logger.warning(
                    "Connection cleanup completed with %d error(s): %s",
                    len(errors),
                    "; ".join(errors),
                )

            self._emit(ConnectionEvent.CLEANUP_DONE)

    def request_stop(self) -> None:
        self._stop_event.set()
