"""QThread wrapper around the async connect orchestration.

پوشش QThread دور orchestration async اتصال.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from bimarz.engine import EngineNotBuiltError
from bimarz.failover import FailoverManager, check_all_profiles, check_profile_health
from bimarz.killswitch_manager import KillSwitchManager, KillSwitchTriggeredError
from bimarz.models import HealthCheckResult, ServerProfile
from bimarz.xray_config import ACTIVE_OUTBOUND_TAG, build_connect_config
from bimarz.xray_manager import BinaryNotFoundError, XrayProcess, find_xray_binary

logger = logging.getLogger(__name__)


def detect_default_interface() -> str:
    """Detect the interface used by the default route (best-effort, Linux-focused).

    تشخیص interface مربوط به مسیر پیش‌فرض (بهترین تلاش ممکن، تمرکز روی لینوکس).
    """
    route_path = Path("/proc/net/route")
    if not route_path.exists():
        # Non-Linux or restricted environment – let KillSwitchManager resolve
        return "auto"

    try:
        with open(route_path, encoding="utf-8") as f:
            next(f)  # skip header
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 11 and fields[1] == "00000000":  # default route
                    iface = fields[0]
                    if iface and iface != "lo":
                        return iface
    except Exception:
        pass

    candidates = [
        "eth0",
        "enp0s3",
        "enp0s8",
        "ens33",
        "wlan0",
        "wlp2s0",
        "rmnet0",
        "tun0",
        "utun0",
    ]
    for name in candidates:
        if Path(f"/sys/class/net/{name}").exists():
            return name

    return "eth0"


class ConnectionWorker(QThread):
    """Runs bimarz connect logic in a background thread so the GUI stays responsive.

    منطق اتصال bimarz را در یک thread پس‌زمینه اجرا می‌کند تا GUI پاسخگو بماند.
    """

    connected = Signal(str)
    disconnected = Signal()
    connection_error = Signal(str)
    latency_updated = Signal(str, float, bool)
    failover_occurred = Signal(str, str)
    killswitch_triggered = Signal(str)

    def __init__(
        self,
        profile: ServerProfile,
        all_profiles: dict[str, ServerProfile] | None = None,
        enable_killswitch: bool = False,
        ks_interface: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._profile = profile
        self._all_profiles = all_profiles
        self._enable_killswitch = enable_killswitch
        self._ks_interface = ks_interface or detect_default_interface()

        self._stop_event = threading.Event()
        self._connected_once = False

        self._loop: asyncio.AbstractEventLoop | None = None
        self._xray_process: XrayProcess | None = None
        self._ks_manager = KillSwitchManager()
        self._client: Any | None = None
        self._runtime_dir: tempfile.TemporaryDirectory | None = None

    def stop(self) -> None:
        """Request graceful disconnection, cancel running tasks and wake the loop."""
        self._stop_event.set()

        loop = self._loop
        if loop is not None and not loop.is_closed():
            try:
                def _cancel_all() -> None:
                    current = asyncio.current_task()
                    for task in asyncio.all_tasks(loop):
                        if task is not current:
                            task.cancel()

                loop.call_soon_threadsafe(_cancel_all)
            except Exception:
                pass

    def should_stop(self) -> bool:
        """Return whether the worker received a stop request."""
        return self._stop_event.is_set()

    def run(self) -> None:
        """Main thread routine: start xray, connect gRPC, optional failover loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._run_connect()

        except EngineNotBuiltError:
            self.connection_error.emit(
                "Rust extension not built. Run: maturin develop --release"
            )

        except BinaryNotFoundError as exc:
            self.connection_error.emit(
                f"xray-core binary not found: {exc}"
            )

        except KillSwitchTriggeredError as exc:
            self.killswitch_triggered.emit(str(exc))

        except Exception as exc:
            logger.exception("Connection worker failed")
            self.connection_error.emit(str(exc))

        finally:
            try:
                self._cleanup()

            finally:
                if self._loop is not None:
                    self._loop.close()
                    self._loop = None

                if self._connected_once:
                    self.disconnected.emit()

    def _run_connect(self) -> None:
        from bimarz.cli import _connect_with_retry, _outbound_kwargs
        from bimarz.engine import get_engine_client_class

        binary_path = find_xray_binary()

        if binary_path is None:
            raise BinaryNotFoundError(
                "xray-core binary not found. Install it or pass --xray-bin."
            )

        # Keep the runtime directory alive for the whole lifetime of the worker
        self._runtime_dir = tempfile.TemporaryDirectory()
        config_path = Path(self._runtime_dir.name) / "connect-runtime.json"

        config_path.write_text(
            build_connect_config(enable_dns_guard=True),
            encoding="utf-8",
        )
        try:
            config_path.chmod(0o600)
        except Exception:
            logger.debug("Failed to set restrictive permissions on runtime config")

        self._xray_process = XrayProcess(
            binary_path=binary_path,
            config_path=config_path,
        )

        self._xray_process.start()

        # Wait until xray process is alive (simple readiness)
        ready_deadline = time.monotonic() + 5.0
        while time.monotonic() < ready_deadline:
            if self._xray_process.is_alive():
                break
            if self.should_stop():
                return
            time.sleep(0.1)
        else:
            raise RuntimeError("xray-core failed to become ready")

        # Connect engine first, then activate kill-switch
        self._run_async_fn(
            self._async_connect,
            get_engine_client_class,
            _connect_with_retry,
            _outbound_kwargs,
        )

        if self._enable_killswitch:
            getuid = getattr(os, "getuid", None)
            xray_uid = getuid() if callable(getuid) else None

            try:
                self._ks_manager.activate(
                    interface=self._ks_interface,
                    xray_uid=xray_uid,
                )
            except Exception:
                logger.exception("Kill-switch activation failed")
                if self._xray_process is not None:
                    try:
                        self._xray_process.stop()
                    except Exception:
                        pass
                raise

            if self._xray_process is None:
                raise RuntimeError(
                    "Xray process was not created."
                )

            self._ks_manager.start_process_watcher(
                poll_fn=self._xray_process.is_alive
            )

        self._connected_once = True
        self.connected.emit(self._profile.remark)

        if self._all_profiles and len(self._all_profiles) > 1:
            manager = FailoverManager(
                active_profile_id=self._profile.profile_id
            )
            self._failover_loop(manager)

        else:
            self._simple_watch_loop()

    def _run_async_fn(
        self,
        fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        timeout: float = 30.0,
    ) -> Any:
        """Run a coroutine-producing function using the worker event loop with timeout."""
        if self._loop is None:
            raise RuntimeError(
                "Worker event loop is not initialized."
            )

        if self._loop.is_closed():
            raise RuntimeError(
                "Worker event loop is already closed."
            )

        return self._loop.run_until_complete(
            asyncio.wait_for(fn(*args), timeout=timeout)
        )

    async def _async_connect(
        self,
        get_engine_client_class: Callable[[], Any],
        connect_with_retry: Callable[..., Coroutine[Any, Any, Any]],
        outbound_kwargs: Callable[[ServerProfile], dict[str, Any]],
    ) -> None:
        client_class = get_engine_client_class()

        self._client = await connect_with_retry(client_class)

        if self._client is None:
            raise RuntimeError(
                "Engine client was not created."
            )

        await self._client.add_vless_reality_outbound(
            **outbound_kwargs(self._profile)
        )

    def _failover_loop(self, manager: FailoverManager) -> None:
        """Background health-check with automatic failover."""
        from bimarz.constants import FAILOVER_CHECK_INTERVAL_SECONDS

        while not self.should_stop():
            self._interruptible_sleep(
                FAILOVER_CHECK_INTERVAL_SECONDS
            )

            if self.should_stop():
                break

            if (
                self._enable_killswitch
                and not self._ks_manager.is_watcher_alive()
            ):
                raise KillSwitchTriggeredError(
                    "xray-core stopped unexpectedly. Kill-switch triggered."
                )

            try:
                self._run_async_fn(
                    self._async_failover_check,
                    manager,
                )

            except KillSwitchTriggeredError:
                raise

            except Exception:
                logger.exception(
                    "Failover iteration failed."
                )

    async def _async_failover_check(
        self,
        manager: FailoverManager,
    ) -> None:
        from bimarz.cli import _outbound_kwargs

        if not self._all_profiles:
            return

        if self._client is None:
            return

        result = await check_profile_health(
            self._profile
        )

        self._emit_latency(result)

        manager.record_active_profile_result(
            result
        )

        if not manager.should_failover():
            return

        all_results = await check_all_profiles(
            list(self._all_profiles.values())
        )

        for health_result in all_results.values():
            self._emit_latency(
                health_result
            )

        next_id = manager.pick_best_alternative(
            all_results
        )

        if next_id is None:
            return

        if next_id == self._profile.profile_id:
            return

        next_profile = self._all_profiles.get(next_id)
        if next_profile is None:
            return

        remove_outbound = getattr(
            self._client,
            "remove_outbound",
            None,
        )
        add_outbound = getattr(
            self._client,
            "add_vless_reality_outbound",
            None,
        )

        if not callable(remove_outbound):
            logger.error(
                "Engine client does not support remove_outbound."
            )
            return

        if not callable(add_outbound):
            logger.error(
                "Engine client does not support add_vless_reality_outbound."
            )
            return

        old_kwargs = _outbound_kwargs(self._profile)
        new_kwargs = _outbound_kwargs(next_profile)

        try:
            await remove_outbound(ACTIVE_OUTBOUND_TAG)
            await add_outbound(**new_kwargs)

        except Exception:
            logger.exception(
                "Failover switch failed. Restoring previous profile."
            )

            try:
                await remove_outbound(ACTIVE_OUTBOUND_TAG)
            except Exception:
                pass

            try:
                await add_outbound(**old_kwargs)
            except Exception:
                logger.exception(
                    "Critical: rollback failed."
                )

            return

        try:
            event = manager.trigger_failover(
                next_id,
                reason=f"{manager.threshold} consecutive failures",
            )
        except Exception:
            logger.exception(
                "Failed updating failover state – rolling back outbound"
            )
            try:
                await remove_outbound(ACTIVE_OUTBOUND_TAG)
            except Exception:
                pass
            try:
                await add_outbound(**old_kwargs)
            except Exception:
                logger.exception(
                    "Critical: state rollback after trigger_failover failure also failed."
                )
            return

        # Keep FailoverManager in sync with the new active profile
        manager.active_profile_id = next_id

        self.failover_occurred.emit(
            event.from_profile_id or "unknown",
            event.to_profile_id,
        )

        self._profile = next_profile

    def _simple_watch_loop(self) -> None:
        """Simple loop when failover is disabled: just watch killswitch."""
        while not self.should_stop():
            if self._stop_event.wait(1.0):
                break

            if (
                self._enable_killswitch
                and not self._ks_manager.is_watcher_alive()
            ):
                raise KillSwitchTriggeredError(
                    "xray-core stopped unexpectedly. Kill-switch triggered."
                )

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep until timeout or stop request."""
        self._stop_event.wait(seconds)

    def _emit_latency(self, result: HealthCheckResult) -> None:
        latency = (
            result.latency_ms
            if result.latency_ms is not None
            else -1.0
        )
        self.latency_updated.emit(
            result.profile_id,
            latency,
            result.reachable,
        )

    def _cleanup(self) -> None:
        if self._loop is not None and not self._loop.is_closed():
            if self._client is not None:
                try:
                    self._run_async_fn(
                        self._async_cleanup,
                        timeout=10.0,
                    )
                except Exception as exc:
                    logger.debug(
                        "Failed to cleanup engine client: %s",
                        exc,
                    )
                finally:
                    self._client = None

        try:
            self._ks_manager.deactivate()

        except Exception as exc:
            logger.debug(
                "Failed to deactivate kill switch: %s",
                exc,
            )

        if self._xray_process is not None:
            try:
                self._xray_process.stop()
            except Exception as exc:
                logger.debug(
                    "Failed to stop xray process: %s",
                    exc,
                )
            finally:
                self._xray_process = None

        if self._runtime_dir is not None:
            try:
                self._runtime_dir.cleanup()
            except Exception as exc:
                logger.debug(
                    "Failed to cleanup runtime directory: %s",
                    exc,
                )
            finally:
                self._runtime_dir = None

    async def _async_cleanup(self) -> None:
        if self._client is None:
            return

        try:
            remove_outbound = getattr(
                self._client,
                "remove_outbound",
                None,
            )

            if callable(remove_outbound):
                await remove_outbound(
                    ACTIVE_OUTBOUND_TAG
                )

        except Exception as exc:
            logger.debug(
                "Failed to remove outbound during cleanup: %s",
                exc,
            )

        try:
            close = getattr(
                self._client,
                "close",
                None,
            )

            if callable(close):
                result = close()

                if asyncio.iscoroutine(result):
                    await result

        except Exception as exc:
            logger.debug(
                "Failed to close engine client: %s",
                exc,
            )
