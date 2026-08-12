"""Kill-switch decision and lifecycle management.

مدیریت تصمیم‌گیری و چرخه عمر kill-switch.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from bimarz.engine import EngineNotBuiltError
from bimarz.models import KillSwitchState, KillSwitchWatcherState
from bimarz.platform_detect import detect_environment
from bimarz.state import console

logger = logging.getLogger(__name__)


class KillSwitchTriggeredError(RuntimeError):
    """Raised when the kill-switch detects unexpected Xray termination.

    زمانی ایجاد می‌شود که kill-switch توقف غیرمنتظره Xray را تشخیص دهد.
    """


class KillSwitchManager:
    """Manage kernel-level and software-fallback kill-switch modes.

    مدیریت حالت کرنل و fallback نرم‌افزاری kill-switch.
    """

    def __init__(self) -> None:
        self._state = KillSwitchState(
            kernel_capable=False,
            active=False,
        )
        self._watcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._watcher_lock = threading.Lock()
        self._state_lock = threading.Lock()

    @property
    def state(self) -> KillSwitchState:
        """Return the current kill-switch state.

        وضعیت فعلی kill-switch را برمی‌گرداند.
        """
        with self._state_lock:
            return self._state

    @property
    def watcher_state(self) -> KillSwitchWatcherState:
        """Return the watcher lifecycle state.

        وضعیت چرخه عمر watcher را برمی‌گرداند.
        """
        with self._state_lock:
            return self._state.watcher_state

    @property
    def trigger_reason(self) -> str | None:
        """Return the kill-switch trigger reason.

        دلیل فعال شدن kill-switch را برمی‌گرداند.
        """
        with self._state_lock:
            return self._state.trigger_reason

    def is_triggered(self) -> bool:
        """Return whether the kill-switch has detected a failure.

        مشخص می‌کند kill-switch یک failure را تشخیص داده است یا خیر.
        """
        with self._state_lock:
            return self._state.triggered

    def is_watcher_alive(self) -> bool:
        """Return whether the watcher thread is currently alive.

        مشخص می‌کند thread مربوط به watcher در حال اجرا است یا خیر.
        """
        with self._watcher_lock:
            thread = self._watcher_thread

        return thread is not None and thread.is_alive()

    def probe_kernel_capability(self) -> bool:
        """Test whether kernel kill-switch rules are usable.

        قابلیت استفاده از قوانین kill-switch در سطح کرنل را بررسی می‌کند.
        """
        try:
            from bimarz._engine_core import probe_kernel_killswitch_capability

            return bool(probe_kernel_killswitch_capability())
        except EngineNotBuiltError:
            return False
        except ImportError:
            return False
        except Exception:
            logger.exception("Kernel kill-switch capability probe failed.")
            return False

    def _set_state(
        self,
        *,
        kernel_capable: bool,
        active: bool,
        interface: str | None,
        xray_uid: int | None,
        watcher_state: KillSwitchWatcherState,
        triggered: bool,
        trigger_reason: str | None,
    ) -> None:
        with self._state_lock:
            self._state = KillSwitchState(
                kernel_capable=kernel_capable,
                active=active,
                interface=interface,
                xray_uid=xray_uid,
                watcher_state=watcher_state,
                triggered=triggered,
                trigger_reason=trigger_reason,
            )

    def activate(self, interface: str, xray_uid: int | None = None) -> None:
        """Activate the best available kill-switch implementation.

        بهترین پیاده‌سازی موجود kill-switch را فعال می‌کند.
        """
        current = self.state

        if current.active:
            if current.interface == interface and current.xray_uid == xray_uid and not current.triggered:
                return

            raise RuntimeError("kill-switch is already active; deactivate it before reactivating")

        env = detect_environment()
        kernel_capable = self.probe_kernel_capability()

        if kernel_capable:
            try:
                from bimarz._engine_core import apply_killswitch_rules

                apply_killswitch_rules(interface, xray_uid)

                self._set_state(
                    kernel_capable=True,
                    active=True,
                    interface=interface,
                    xray_uid=xray_uid,
                    watcher_state=KillSwitchWatcherState.NOT_STARTED,
                    triggered=False,
                    trigger_reason=None,
                )

                console.print(f"[green]kill-switch[/green] kernel-level active on {interface}")
                return
            except EngineNotBuiltError:
                logger.warning("Rust extension unavailable while applying kernel kill-switch rules.")
            except Exception as exc:
                logger.warning(
                    "Kernel kill-switch application failed: %s. Using software fallback.",
                    exc,
                )

        self._set_state(
            kernel_capable=False,
            active=True,
            interface=interface,
            xray_uid=xray_uid,
            watcher_state=KillSwitchWatcherState.NOT_STARTED,
            triggered=False,
            trigger_reason=None,
        )

        console.print(
            "[yellow]warning:[/yellow] kernel-level kill-switch unavailable in "
            f"this environment ({env.value}). Using software-fallback mode."
        )

    def _trigger(self, reason: str) -> None:
        with self._state_lock:
            if self._stop_event.is_set():
                return

            if not self._state.active:
                return

            self._state = KillSwitchState(
                kernel_capable=self._state.kernel_capable,
                active=True,
                interface=self._state.interface,
                xray_uid=self._state.xray_uid,
                watcher_state=KillSwitchWatcherState.PROCESS_DIED,
                triggered=True,
                trigger_reason=reason,
            )

        self._stop_event.set()
        logger.error("Kill-switch triggered: %s", reason)

    def start_process_watcher(
        self,
        poll_fn: Callable[[], bool],
        interval_seconds: float = 1.0,
    ) -> None:
        """Start exactly one Xray liveness watcher.

        دقیقاً یک watcher برای پایش زنده بودن Xray اجرا می‌کند.
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")

        with self._watcher_lock:
            current = self._watcher_thread

            if current is not None and current.is_alive():
                return

            with self._state_lock:
                if self._state.watcher_state == KillSwitchWatcherState.PROCESS_DIED:
                    raise RuntimeError("kill-switch watcher cannot restart after a trigger")

                self._state = KillSwitchState(
                    kernel_capable=self._state.kernel_capable,
                    active=self._state.active,
                    interface=self._state.interface,
                    xray_uid=self._state.xray_uid,
                    watcher_state=KillSwitchWatcherState.RUNNING,
                    triggered=False,
                    trigger_reason=None,
                )

            self._stop_event.clear()

            def watcher() -> None:
                try:
                    while not self._stop_event.is_set():
                        try:
                            alive = poll_fn()
                        except Exception as exc:
                            if self._stop_event.is_set():
                                return

                            logger.error(
                                "Kill-switch process watcher failed: %s",
                                exc,
                            )
                            self._trigger(f"Xray liveness check failed: {exc}")
                            return

                        if not alive:
                            if self._stop_event.is_set():
                                return

                            self._trigger("xray-core unexpectedly stopped")
                            return

                        if self._stop_event.wait(interval_seconds):
                            return
                finally:
                    with self._state_lock:
                        current_state = self._state

                        if current_state.watcher_state == KillSwitchWatcherState.RUNNING:
                            self._state = KillSwitchState(
                                kernel_capable=current_state.kernel_capable,
                                active=current_state.active,
                                interface=current_state.interface,
                                xray_uid=current_state.xray_uid,
                                watcher_state=KillSwitchWatcherState.STOPPED,
                                triggered=current_state.triggered,
                                trigger_reason=current_state.trigger_reason,
                            )

                    with self._watcher_lock:
                        if threading.current_thread() is self._watcher_thread:
                            self._watcher_thread = None

            thread = threading.Thread(
                target=watcher,
                name="bimarz-killswitch-watcher",
                daemon=True,
            )

            self._watcher_thread = thread
            thread.start()

    def stop_process_watcher(self) -> bool:
        """Stop the watcher and report whether it stopped successfully.

        watcher را متوقف کرده و موفقیت توقف آن را گزارش می‌کند.
        """
        self._stop_event.set()

        with self._watcher_lock:
            thread = self._watcher_thread

        if thread is None:
            with self._state_lock:
                if self._state.watcher_state == KillSwitchWatcherState.RUNNING:
                    self._state = KillSwitchState(
                        kernel_capable=self._state.kernel_capable,
                        active=self._state.active,
                        interface=self._state.interface,
                        xray_uid=self._state.xray_uid,
                        watcher_state=KillSwitchWatcherState.STOPPED,
                        triggered=self._state.triggered,
                        trigger_reason=self._state.trigger_reason,
                    )
            return True

        if thread is threading.current_thread():
            return False

        thread.join(timeout=2.0)

        if thread.is_alive():
            logger.error("Kill-switch watcher did not stop within the timeout.")
            return False

        with self._watcher_lock:
            if self._watcher_thread is thread:
                self._watcher_thread = None

        with self._state_lock:
            if self._state.watcher_state == KillSwitchWatcherState.RUNNING:
                self._state = KillSwitchState(
                    kernel_capable=self._state.kernel_capable,
                    active=self._state.active,
                    interface=self._state.interface,
                    xray_uid=self._state.xray_uid,
                    watcher_state=KillSwitchWatcherState.STOPPED,
                    triggered=self._state.triggered,
                    trigger_reason=self._state.trigger_reason,
                )

        return True

    def deactivate(self) -> None:
        """Safely remove kernel rules and stop the watcher.

        قوانین کرنل را حذف کرده و watcher را متوقف می‌کند.
        """
        current = self.state

        if current.kernel_capable and current.active and current.interface is not None:
            try:
                from bimarz._engine_core import remove_killswitch_rules

                remove_killswitch_rules(
                    current.interface,
                    current.xray_uid,
                )
            except Exception:
                logger.exception("Failed to remove kernel kill-switch rules; keeping kill-switch active.")
                return

        if not self.stop_process_watcher():
            logger.error("Kill-switch watcher could not be stopped; keeping kill-switch active.")
            return

        self._set_state(
            kernel_capable=current.kernel_capable,
            active=False,
            interface=None,
            xray_uid=None,
            watcher_state=KillSwitchWatcherState.STOPPED,
            triggered=current.triggered,
            trigger_reason=current.trigger_reason,
        )

        console.print("[green]kill-switch[/green] deactivated")
