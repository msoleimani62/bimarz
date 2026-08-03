"""
Kill-switch control service.
سرویس کنترل kill-switch.
"""

from __future__ import annotations

from bimarz.helpers import get_current_uid
from bimarz.killswitch_manager import KillSwitchManager


class KillSwitchService:
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

    def is_active(self) -> bool:
        return self.manager.state.active

    def is_watcher_alive(self) -> bool:
        return self.manager.is_watcher_alive()
