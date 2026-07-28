"""Pure dataclasses with zero UI dependency, mirroring the
`models.py` pattern already proven in open-downloader-cli: designed from
day one to be reusable by a future desktop GUI or Android app without any
rewrite.

دیتاکلاس‌های خالص و بدون وابستگی به UI، مطابق همان الگوی `models.py` که در
open-downloader-cli جواب داده؛ از همان ابتدا طوری طراحی شده‌اند که یک GUI
دسکتاپ یا اپ اندروید آینده بتواند بدون بازنویسی از آن‌ها استفاده کند.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Environment(str, Enum):
    """Detected runtime environment, same taxonomy as open-downloader-cli.

    محیط اجرای شناسایی‌شده، با همان دسته‌بندی open-downloader-cli.
    """

    ANDROID_TERMUX = "android_termux"
    KALI_NETHUNTER = "kali_nethunter"
    DESKTOP_LINUX = "desktop_linux"
    WSL = "wsl"
    OTHER = "other"


@dataclass(frozen=True)
class VlessRealityOutbound:
    """All fields needed to describe a single VLESS + Reality + Vision
    outbound, parsed from a vless:// share link. This is intentionally the
    only protocol/security combination this project parses — see
    subscription.py for why.

    تمام فیلدهای لازم برای توصیف یک outbound از نوع VLESS + Reality +
    Vision، که از یک لینک اشتراک vless:// پارس شده. این عمداً تنها
    ترکیب پروتکل/امنیتی است که این پروژه پارس می‌کند — دلیلش در
    subscription.py توضیح داده شده.
    """

    uuid: str
    address: str
    port: int
    flow: str
    network: str
    security: str
    sni: str
    fingerprint: str
    public_key: str
    short_id: str
    spider_x: str
    remark: str


@dataclass(frozen=True)
class ServerProfile:
    """A single saved server profile (one VLESS+Reality+Vision endpoint).

    یک پروفایل سرور ذخیره‌شده (یک نقطه‌ی اتصال VLESS+Reality+Vision).
    """

    profile_id: str
    tag: str
    remark: str
    outbound_config: dict
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
    """Record of an automatic failover switch, kept for the audit log.

    ثبت یک رویداد سوییچ خودکار failover، برای لاگ حسابرسی.

    NOTE: never include raw UUIDs/private keys here — only opaque
    `profile_id`/`tag` values, per the project's logging rule.

    نکته: هرگز UUID/کلید خصوصی خام اینجا قرار نگیرد — فقط مقادیر مبهم
    `profile_id`/`tag`، طبق قانون لاگ‌نویسی پروژه.
    """

    from_profile_id: str | None
    to_profile_id: str
    reason: str
    occurred_at_iso: str


@dataclass
class DoctorReport:
    """Everything `bimarz doctor` prints, collected as data first so both the
    CLI and a future GUI can render it independently.

    هر چیزی که `bimarz doctor` چاپ می‌کند، ابتدا به‌صورت داده جمع‌آوری می‌شود تا
    هم CLI و هم یک GUI آینده بتوانند مستقل آن را نمایش دهند.
    """

    bimarz_version: str
    environment: Environment
    xray_binary_found: bool
    xray_binary_path: str | None
    xray_version: str | None
    grpc_reachable: bool
    profiles_count: int
    warnings: list[str] = field(default_factory=list)
