"""Health-checking and automatic failover logic — phase 3.

Two independent pieces:
1. Async functions that health-check one or all saved profiles by
   delegating to the Rust extension (raw TCP probes against each
   server, run in parallel for the "all profiles" case).
2. `FailoverManager`, a pure/testable state machine that decides WHEN to
   fail over (consecutive-failure counting) and WHERE to fail over to
   (lowest-latency reachable alternative) — it never touches the network
   itself, so it can be fully unit-tested without mocking gRPC or TCP.

منطق تست سلامت و سوییچ خودکار — فاز ۳.

دو بخش مستقل:
۱. توابع async که یک یا همه‌ی پروفایل‌های ذخیره‌شده را با واگذاری به
   ماژول Rust تست سلامت می‌کنند (اتصال TCP خام به هر سرور، برای حالت
   «همه‌ی پروفایل‌ها» به‌صورت موازی اجرا می‌شود).
۲. `FailoverManager`، یک ماشین‌حالت خالص/قابل‌تست که تصمیم می‌گیرد «کِی»
   سوییچ کند (شمارش شکست‌های متوالی) و «به کجا» سوییچ کند (پایین‌ترین
   تاخیر در بین گزینه‌های در‌دسترس) — خودش هرگز مستقیم با شبکه کار
   نمی‌کند، پس کاملاً بدون نیاز به mock کردن gRPC یا TCP قابل تست است.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bimarz.constants import FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD, HEALTHCHECK_TIMEOUT_SECONDS
from bimarz.models import FailoverEvent, HealthCheckResult, ServerProfile


async def check_profile_health(profile: ServerProfile) -> HealthCheckResult:
    """Health-checks a single profile's server directly (not through the
    xray-core tunnel).

    سرور یک پروفایل را مستقیم تست سلامت می‌کند (نه از طریق تونل xray-core).
    """
    from bimarz.engine import get_health_check_function

    check_fn = get_health_check_function()
    outbound = profile.outbound_config
    timeout_ms = int(HEALTHCHECK_TIMEOUT_SECONDS * 1000)

    reachable, latency_ms, error_message = await check_fn(
        outbound["address"], int(outbound["port"]), timeout_ms
    )

    return HealthCheckResult(
        profile_id=profile.profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso=datetime.now(timezone.utc).isoformat(),
        error_message=error_message,
    )


async def check_all_profiles(profiles: list[ServerProfile]) -> dict[str, HealthCheckResult]:
    """Health-checks every given profile in parallel (via the Rust batch
    function), returning a dict keyed by profile_id for easy lookup.

    همه‌ی پروفایل‌های داده‌شده را به‌صورت موازی تست سلامت می‌کند (از طریق
    تابع batch در Rust)، و یک دیکشنری بر اساس profile_id برمی‌گرداند تا
    جستجو راحت باشد.
    """
    from bimarz.engine import get_batch_health_check_function

    if not profiles:
        return {}

    check_many_fn = get_batch_health_check_function()
    timeout_ms = int(HEALTHCHECK_TIMEOUT_SECONDS * 1000)
    targets = [
        (profile.profile_id, profile.outbound_config["address"], int(profile.outbound_config["port"]))
        for profile in profiles
    ]

    raw_results = await check_many_fn(targets, timeout_ms)
    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        profile_id: HealthCheckResult(
            profile_id=profile_id,
            reachable=reachable,
            latency_ms=latency_ms,
            checked_at_iso=now_iso,
            error_message=error_message,
        )
        for profile_id, reachable, latency_ms, error_message in raw_results
    }


class FailoverManager:
    """Tracks consecutive health-check failures for the currently active
    profile and decides when/where to fail over. Holds no network state —
    every method takes results it's handed, so it's trivial to unit-test
    with fake HealthCheckResult values.

    شمارش شکست‌های متوالی تست سلامت برای پروفایل فعال فعلی را نگه می‌دارد
    و تصمیم می‌گیرد کِی/به‌کجا سوییچ کند. هیچ حالت شبکه‌ای نگه نمی‌دارد —
    هر متد نتایجی که بهش داده می‌شه رو می‌گیره، پس تست‌کردنش با مقادیر
    HealthCheckResult ساختگی خیلی ساده‌ست.
    """

    def __init__(
        self,
        active_profile_id: str,
        consecutive_failure_threshold: int = FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD,
    ) -> None:
        self._active_profile_id = active_profile_id
        self._threshold = consecutive_failure_threshold
        self._consecutive_failures = 0
        self.events: list[FailoverEvent] = []

    @property
    def active_profile_id(self) -> str:
        return self._active_profile_id

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def threshold(self) -> int:
        return self._threshold

    def record_active_profile_result(self, result: HealthCheckResult) -> None:
        """Feeds one health-check result for the CURRENTLY ACTIVE
        profile, updating the consecutive-failure counter. Results for
        any other profile_id are ignored (use pick_best_alternative for
        those).

        یک نتیجه‌ی تست سلامت برای پروفایل فعال فعلی می‌دهد و شمارنده‌ی
        شکست‌های متوالی را به‌روز می‌کند. نتایج مربوط به پروفایل‌های دیگر
        نادیده گرفته می‌شوند (برای آن‌ها از pick_best_alternative استفاده
        کنید).
        """
        if result.profile_id != self._active_profile_id:
            return
        if result.reachable:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

    def should_failover(self) -> bool:
        """Whether the consecutive-failure count has crossed the threshold.

        آیا شمارش شکست‌های متوالی از آستانه گذشته است.
        """
        return self._consecutive_failures >= self._threshold

    def pick_best_alternative(self, all_results: dict[str, HealthCheckResult]) -> str | None:
        """Given a fresh round of results for ALL profiles, returns the
        profile_id of the best reachable alternative (lowest latency),
        excluding the currently active one. None if no alternative is
        reachable.

        با در دست داشتن یک دور تازه از نتایج برای همه‌ی پروفایل‌ها،
        profile_id بهترین گزینه‌ی جایگزین در‌دسترس (کمترین تاخیر) را
        برمی‌گرداند، به‌جز پروفایل فعال فعلی. اگر هیچ جایگزینی در‌دسترس
        نباشد None برمی‌گرداند.
        """
        candidates = [
            (result.profile_id, result.latency_ms)
            for result in all_results.values()
            if result.profile_id != self._active_profile_id
            and result.reachable
            and result.latency_ms is not None
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[1])
        return candidates[0][0]

    def trigger_failover(self, to_profile_id: str, reason: str) -> FailoverEvent:
        """Records the switch and resets the failure counter for the new
        active profile.

        سوییچ را ثبت می‌کند و شمارنده‌ی شکست را برای پروفایل فعال جدید
        صفر می‌کند.
        """
        event = FailoverEvent(
            from_profile_id=self._active_profile_id,
            to_profile_id=to_profile_id,
            reason=reason,
            occurred_at_iso=datetime.now(timezone.utc).isoformat(),
        )
        self._active_profile_id = to_profile_id
        self._consecutive_failures = 0
        self.events.append(event)
        return event
