"""
Kill-switch control service.
سرویس کنترل kill-switch.
"""

from __future__ import annotations

from collections.abc import Callable

from bimarz.helpers import get_current_uid
from bimarz.killswitch_manager import KillSwitchManager


class KillSwitchService:
    """Application-facing kill-switch lifecycle service.

    سرویس سطح برنامه برای مدیریت چرخه عمر kill-switch.
    """

    def __init__(self, manager: KillSwitchManager | None = None) -> None:
        self.manager = manager or KillSwitchManager()

    def enable(self, interface: str = "tun0", uid: int | None = None) -> None:
        """Activate the kill-switch.

        kill-switch را فعال می‌کند.
        """
        if uid is None:
            uid = get_current_uid()

        self.manager.activate(interface=interface, xray_uid=uid)

    def disable(self) -> None:
        """Deactivate the kill-switch.

        kill-switch را غیرفعال می‌کند.
        """
        self.manager.deactivate()

    def start_watcher(
        self,
        poll_fn: Callable[[], bool],
        interval_seconds: float = 1.0,
    ) -> None:
        """Start the Xray process watcher.

        watcher پردازش Xray را شروع می‌کند.
        """
        self.manager.start_process_watcher(
            poll_fn=poll_fn,
            interval_seconds=interval_seconds,
        )

    def stop_watcher(self) -> None:
        """Stop the Xray process watcher.

        watcher پردازش Xray را متوقف می‌کند.
        """
        self.manager.stop_process_watcher()

    def is_active(self) -> bool:
        """Return whether the kill-switch is active.

        وضعیت فعال بودن kill-switch را برمی‌گرداند.
        """
        return self.manager.state.active

    def is_watcher_alive(self) -> bool:
        """Return whether the process watcher is alive.

        وضعیت زنده بودن watcher را برمی‌گرداند.
        """
        return self.manager.is_watcher_alive()
