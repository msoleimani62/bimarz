"""Pure dataclasses with zero UI dependency.

دیتاکلاس‌های خالص و بدون وابستگی به UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Environment(str, Enum):
    """Detected runtime environment.

    محیط اجرای شناسایی‌شده.
    """

    ANDROID_TERMUX = "android_termux"
    KALI_NETHUNTER = "kali_nethunter"
    DESKTOP_LINUX = "desktop_linux"
    WSL = "wsl"
    OTHER = "other"


class GrpcStatus(str, Enum):
    """Four-level gRPC health status for `bimarz doctor`.

    چهار سطح وضعیت سلامت gRPC برای `bimarz doctor`.
    """

    NOT_CHECKED = "not_checked"
    UNREACHABLE = "unreachable"
    LISTENING = "listening"
    RESPONDING = "responding"

    not_checked = NOT_CHECKED
    unreachable = UNREACHABLE
    listening = LISTENING
    responding = RESPONDING


@dataclass(frozen=True)
class ServerProfile:
    """A single saved server profile.

    یک پروفایل سرور ذخیره‌شده.
    """

    profile_id: str
    tag: str
    remark: str
    outbound_config: dict[str, Any]
    added_at_iso: str


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single health check against one server.

    نتیجه‌ی یک تست سلامت روی یک سرور.
    """

    profile_id: str
    reachable: bool
    latency_ms: float | None
    checked_at_iso: str
    error_message: str | None = None


@dataclass(frozen=True)
class FailoverEvent:
    """Record of an automatic failover switch.

    ثبت یک رویداد سوییچ خودکار failover.

    NOTE: never include raw UUIDs/private keys here.
    نکته: هرگز UUID/کلید خصوصی خام اینجا قرار نگیرد.
    """

    from_profile_id: str | None
    to_profile_id: str
    reason: str
    occurred_at_iso: str


@dataclass
class DoctorReport:
    """Everything `bimarz doctor` prints, collected as data first.

    هر چیزی که `bimarz doctor` چاپ می‌کند، ابتدا به‌صورت داده جمع‌آوری می‌شود.
    """

    bimarz_version: str
    environment: Environment
    xray_binary_found: bool
    xray_binary_path: str | None
    xray_version: str | None
    grpc_status: GrpcStatus
    grpc_endpoint: str
    profiles_count: int
    # وضعیت فعلی kill-switch.
    # Current kill-switch state.
    killswitch_active: bool = False
    warnings: list[str] = field(default_factory=list)


class KillSwitchWatcherState(str, Enum):
    """Lifecycle state of the kill-switch process watcher.

    وضعیت چرخه عمر watcher مربوط به kill-switch.
    """

    NOT_STARTED = "not_started"
    RUNNING = "running"
    STOPPED = "stopped"
    PROCESS_DIED = "process_died"


@dataclass(frozen=True)
class KillSwitchState:
    """Current state of the kill-switch.

    وضعیت فعلی kill-switch.
    """

    kernel_capable: bool
    active: bool
    interface: str | None = None
    xray_uid: int | None = None
    watcher_state: KillSwitchWatcherState = KillSwitchWatcherState.NOT_STARTED
    triggered: bool = False
    trigger_reason: str | None = None


@dataclass(frozen=True)
class DNSGuardConfig:
    """Configuration for DNS leak protection.

    کانفیگ محافظت در برابر نشت DNS.
    """

    doh_server: str = "https+local://1.1.1.1/dns-query"
    query_strategy: str = "UseIP"
    tag: str = "dns-out"
