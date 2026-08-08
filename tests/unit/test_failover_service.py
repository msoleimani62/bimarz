"""Unit tests for bimarz.services.failover.

Pure state-machine tests — no network needed.

تست‌های واحد برای bimarz.services.failover.

تست‌های ماشین‌حالت خالص — بدون شبکه.
"""

from __future__ import annotations

from bimarz.models import HealthCheckResult
from bimarz.services.failover import FailoverService


def build_result(
    profile_id: str,
    reachable: bool,
    latency_ms: float | None = None,
) -> HealthCheckResult:
    return HealthCheckResult(
        profile_id=profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso="2026-08-07T00:00:00+00:00",
        error_message=None,
    )


def test_service_trigger_updates_active_id() -> None:
    """FailoverService.trigger changes the active profile."""
    svc = FailoverService(initial_profile_id="p1")

    svc.trigger("p2", reason="manual")

    assert svc.active_id == "p2"


def test_service_pick_best_returns_none_when_no_alternatives() -> None:
    """pick_best returns None when every other profile is unreachable."""
    svc = FailoverService(initial_profile_id="p1")

    results = {
        "p1": build_result("p1", True, 10.0),
        "p2": build_result("p2", False),
    }

    assert svc.pick_best(results) is None


def test_service_pick_best_ignores_active_profile() -> None:
    """pick_best never returns the currently active profile."""
    svc = FailoverService(initial_profile_id="p1")

    results = {
        "p1": build_result("p1", True, 1.0),
        "p2": build_result("p2", True, 50.0),
    }

    assert svc.pick_best(results) == "p2"
