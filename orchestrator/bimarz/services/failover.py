"""
Failover decision service.

سرویس تصمیم‌گیری failover.
"""

from __future__ import annotations

from bimarz.failover import FailoverManager
from bimarz.models import FailoverEvent, HealthCheckResult


class FailoverService:
    def __init__(
        self,
        initial_profile_id: str,
        consecutive_failure_threshold: int | None = None,
    ) -> None:
        if consecutive_failure_threshold is None:
            self.manager = FailoverManager(initial_profile_id)
        else:
            self.manager = FailoverManager(
                initial_profile_id,
                consecutive_failure_threshold=consecutive_failure_threshold,
            )

    def record(self, health: HealthCheckResult) -> None:
        self.manager.record_active_profile_result(health)

    def should_trigger(self) -> bool:
        return self.manager.should_failover()

    def pick_best(
        self,
        all_results: dict[str, HealthCheckResult],
    ) -> str | None:
        return self.manager.pick_best_alternative(all_results)

    def trigger(
        self,
        profile_id: str,
        reason: str = "failover triggered",
    ) -> FailoverEvent:
        return self.manager.trigger_failover(profile_id, reason)

    @property
    def active_id(self) -> str:
        return self.manager.active_profile_id
