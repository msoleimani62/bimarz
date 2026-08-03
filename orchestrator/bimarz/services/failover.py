"""
Failover decision service (thin wrapper around FailoverManager).
سرویس تصمیم‌گیری failover (پوشش نازک روی FailoverManager).
"""

from __future__ import annotations

from bimarz.failover import FailoverManager
from bimarz.models import HealthCheckResult


class FailoverService:
    def __init__(self, initial_profile_id: str) -> None:
        self.manager = FailoverManager(initial_profile_id)

    def record(self, health: HealthCheckResult) -> None:
        self.manager.record_active_profile_result(health)

    def should_trigger(self) -> bool:
        return self.manager.should_failover()

    def pick_best(self, all_results: dict[str, HealthCheckResult]) -> str | None:
        return self.manager.pick_best_alternative(all_results)

    def trigger(self, profile_id: str) -> None:
        self.manager.trigger_failover(
            profile_id, reason=f"{self.manager.threshold} consecutive failures"
        )

    @property
    def active_id(self) -> str:
        return self.manager.active_profile_id
