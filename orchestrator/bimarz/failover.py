"""
Health-checking and automatic failover logic.

منطق تست سلامت و سوییچ خودکار.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bimarz.constants import (
    FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD,
    HEALTHCHECK_TIMEOUT_SECONDS,
)
from bimarz.models import FailoverEvent, HealthCheckResult, ServerProfile


async def check_profile_health(profile: ServerProfile) -> HealthCheckResult:
    """Health-check a single profile directly.

    تست سلامت مستقیم یک پروفایل.
    """
    from bimarz.engine import get_health_check_function

    check_fn = get_health_check_function()
    outbound = profile.outbound_config
    timeout_ms = int(HEALTHCHECK_TIMEOUT_SECONDS * 1000)

    reachable, latency_ms, error_message = await check_fn(
        str(outbound["address"]),
        int(outbound["port"]),
        timeout_ms,
    )

    return HealthCheckResult(
        profile_id=profile.profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso=datetime.now(timezone.utc).isoformat(),
        error_message=error_message,
    )


async def check_all_profiles(
    profiles: list[ServerProfile],
) -> dict[str, HealthCheckResult]:
    """Health-check all profiles concurrently through Rust.

    تست سلامت همه پروفایل‌ها را به‌صورت موازی از طریق Rust انجام می‌دهد.
    """
    from bimarz.engine import get_batch_health_check_function

    if not profiles:
        return {}

    check_many_fn = get_batch_health_check_function()
    timeout_ms = int(HEALTHCHECK_TIMEOUT_SECONDS * 1000)

    targets = [
        (
            profile.profile_id,
            str(profile.outbound_config["address"]),
            int(profile.outbound_config["port"]),
        )
        for profile in profiles
    ]

    raw_results = await check_many_fn(targets, timeout_ms)
    checked_at_iso = datetime.now(timezone.utc).isoformat()

    results: dict[str, HealthCheckResult] = {}

    for profile_id, reachable, latency_ms, error_message in raw_results:
        results[profile_id] = HealthCheckResult(
            profile_id=profile_id,
            reachable=reachable,
            latency_ms=latency_ms,
            checked_at_iso=checked_at_iso,
            error_message=error_message,
        )

    return results


class FailoverManager:
    """Pure failover state machine.

    ماشین حالت خالص تصمیم‌گیری failover.
    """

    def __init__(
        self,
        active_profile_id: str,
        consecutive_failure_threshold: int = FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD,
    ) -> None:
        if not active_profile_id:
            raise ValueError("active_profile_id must not be empty")

        if consecutive_failure_threshold < 1:
            raise ValueError("consecutive_failure_threshold must be at least 1")

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

    def record_active_profile_result(
        self,
        result: HealthCheckResult,
    ) -> None:
        """Record a result belonging to the active profile.

        نتیجه مربوط به پروفایل فعال را ثبت می‌کند.
        """
        if result.profile_id != self._active_profile_id:
            return

        if result.reachable:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

    def should_failover(self) -> bool:
        """Return whether failover threshold has been reached.

        مشخص می‌کند آستانه failover رسیده است یا نه.
        """
        return self._consecutive_failures >= self._threshold

    def pick_best_alternative(
        self,
        all_results: dict[str, HealthCheckResult],
    ) -> str | None:
        """Select the lowest-latency reachable alternative.

        کم‌تاخیرترین پروفایل جایگزین در دسترس را انتخاب می‌کند.
        """
        candidates = [
            result
            for result in all_results.values()
            if (result.profile_id != self._active_profile_id and result.reachable and result.latency_ms is not None)
        ]

        if not candidates:
            return None

        best = min(
            candidates,
            key=lambda result: (result.latency_ms, result.profile_id),
        )
        return best.profile_id

    def trigger_failover(
        self,
        to_profile_id: str,
        reason: str,
    ) -> FailoverEvent:
        """Switch the active profile and record the event.

        پروفایل فعال را تغییر داده و رویداد را ثبت می‌کند.
        """
        if not to_profile_id:
            raise ValueError("to_profile_id must not be empty")

        if to_profile_id == self._active_profile_id:
            raise ValueError("cannot fail over to the active profile")

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
