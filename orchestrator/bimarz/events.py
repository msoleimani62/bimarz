"""
Event system: event types, payload shape and handler signature.
سیستم رویداد: انواع رویداد، شکل payload و امضای هندلر.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import TypedDict


class ConnectionEvent(Enum):
    STARTED = auto()
    ENGINE_READY = auto()
    KILLSWITCH_ENABLED = auto()
    FAILOVER_TRIGGERED = auto()
    KILLSWITCH_WATCHER_DIED = auto()
    PROCESS_STOPPED = auto()
    CLEANUP_DONE = auto()
    ERROR = auto()


class EventPayload(TypedDict, total=False):
    profile_id: str
    new_profile_id: str
    error: str
    message: str


EventHandler = Callable[[ConnectionEvent, EventPayload], None]
