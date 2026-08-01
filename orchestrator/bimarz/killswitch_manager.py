"""Kill-switch decision layer: probe kernel capability, apply/remove rules,
and handle the software fallback when kernel-level is unavailable.

لایه‌ی تصمیم‌گیری kill-switch: آزمایش قابلیت کرنل، اعمال/حذف قوانین، و
مدیریت fallback نرم‌افزاری وقتی kill-switch سطح کرنل در دسترس نیست.
"""

from __future__ import annotations

import threading
from typing import Callable

from bimarz.engine import EngineNotBuiltError
from bimarz.models import KillSwitchState
from bimarz.platform_detect import detect_environment
from bimarz.state import console


class KillSwitchTriggeredError(Exception):
    """Raised when the kill-switch fires (xray-core died unexpectedly).

    زمانی پرتاب می‌شود که kill-switch فعال شود (xray-core غیرمنتظره مرد).
    """


class KillSwitchManager:
    """Manages kernel-level or software-fallback kill-switch.

    Kernel level: uses iptables rules via the Rust extension.
    Software fallback: watches the xray-core process and exits cleanly
    with a warning if it dies unexpectedly.
    """

    def __init__(self) -> None:
        self._state = KillSwitchState(kernel_capable=False, active=False)
        self._watcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def state(self) -> KillSwitchState:
        return self._state

    def probe_kernel_capability(self) -> bool:
        """Tests whether we can actually write and delete iptables rules."""
        try:
            from bimarz._engine_core import probe_kernel_killswitch_capability
            return probe_kernel_killswitch_capability()
        except EngineNotBuiltError:
            return False

    def activate(self, interface: str, xray_uid: int | None = None) -> None:
        """Activates the best available kill-switch for this environment."""
        env = detect_environment()
        kernel_capable = self.probe_kernel_capability()

        if kernel_capable:
            self._state = KillSwitchState(
                kernel_capable=True, active=True, interface=interface, xray_uid=xray_uid
            )
            try:
                from bimarz._engine_core import apply_killswitch_rules
                apply_killswitch_rules(interface, xray_uid)
                console.print(
                    f"[green]kill-switch[/green] kernel-level active on {interface}"
                )
            except EngineNotBuiltError:
                console.print(
                    "[yellow]warning:[/yellow] Rust extension not built, cannot apply kernel rules"
                )
            except Exception as exc:
                console.print(
                    f"[yellow]warning:[/yellow] failed to apply kernel rules: {exc}. "
                    "Falling back to software mode."
                )
                self._state = KillSwitchState(
                    kernel_capable=False, active=True, interface=interface, xray_uid=xray_uid
                )
        else:
            self._state = KillSwitchState(
                kernel_capable=False, active=True, interface=interface, xray_uid=xray_uid
            )
            console.print(
                "[yellow]warning:[/yellow] kernel-level kill-switch unavailable in this "
                f"environment ({env.value}). Using software-fallback mode: if xray-core "
                "dies unexpectedly, the process will exit immediately to prevent leaks."
            )

    def start_process_watcher(
        self,
        poll_fn: Callable[[], bool],
        interval_seconds: float = 1.0,
    ) -> None:
        """Starts a background thread that polls xray-core liveness.

        When the process is detected dead, the watcher stops itself; the
        caller should check is_watcher_alive() to detect the trigger.
        """
        self._stop_event.clear()

        def watcher() -> None:
            while not self._stop_event.is_set():
                if not poll_fn():
                    return
                self._stop_event.wait(interval_seconds)

        self._watcher_thread = threading.Thread(target=watcher, daemon=True)
        self._watcher_thread.start()

    def is_watcher_alive(self) -> bool:
        """Returns True if the watcher thread is still running."""
        if self._watcher_thread is None:
            return False
        return self._watcher_thread.is_alive()

    def stop_process_watcher(self) -> None:
        self._stop_event.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=2.0)

    def deactivate(self) -> None:
        """Removes any active kill-switch rules."""
        if self._state.kernel_capable and self._state.active and self._state.interface is not None:
            try:
                from bimarz._engine_core import remove_killswitch_rules
                remove_killswitch_rules(self._state.interface, self._state.xray_uid)
            except Exception:
                pass
        self._state = KillSwitchState(
            kernel_capable=self._state.kernel_capable, active=False
        )
        self.stop_process_watcher()
        console.print("[green]kill-switch[/green] deactivated")
