"""Tests for failover decision logic.

These tests validate FailoverManager and FailoverService behavior without
network access or Rust extension requirements.
"""

from __future__ import annotations

from bimarz.failover import FailoverManager
from bimarz.models import HealthCheckResult
from bimarz.services.failover import FailoverService


def build_health_result(
    profile_id: str,
    reachable: bool,
    latency_ms: float | None = None,
) -> HealthCheckResult:
    return HealthCheckResult(
        profile_id=profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso="2026-07-28T00:00:00+00:00",
        error_message=None if reachable else "unreachable",
    )


def test_healthy_result_keeps_failure_count_zero() -> None:
    manager = FailoverManager(active_profile_id="p1")

    manager.record_active_profile_result(build_health_result("p1", True, 50.0))

    assert manager.consecutive_failures == 0
    assert manager.should_failover() is False


def test_failures_below_threshold_do_not_trigger_failover() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=3,
    )

    manager.record_active_profile_result(build_health_result("p1", False))
    manager.record_active_profile_result(build_health_result("p1", False))

    assert manager.consecutive_failures == 2
    assert manager.should_failover() is False


def test_threshold_failure_count_triggers_failover() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=3,
    )

    for _ in range(3):
        manager.record_active_profile_result(build_health_result("p1", False))

    assert manager.should_failover() is True


def test_success_after_failure_resets_counter() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=3,
    )

    manager.record_active_profile_result(build_health_result("p1", False))
    manager.record_active_profile_result(build_health_result("p1", False))
    manager.record_active_profile_result(build_health_result("p1", True, 30.0))

    assert manager.consecutive_failures == 0


def test_non_active_profile_results_are_ignored() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=3,
    )

    manager.record_active_profile_result(build_health_result("p1", False))
    manager.record_active_profile_result(build_health_result("p2", True, 10.0))

    assert manager.consecutive_failures == 1


def test_best_alternative_uses_lowest_latency() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p1": build_health_result("p1", False),
        "p2": build_health_result("p2", True, 120.0),
        "p3": build_health_result("p3", True, 45.0),
        "p4": build_health_result("p4", False),
    }

    assert manager.pick_best_alternative(results) == "p3"


def test_best_alternative_excludes_active_profile() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p1": build_health_result("p1", True, 1.0),
        "p2": build_health_result("p2", True, 999.0),
    }

    assert manager.pick_best_alternative(results) == "p2"


def test_best_alternative_returns_none_when_unavailable() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p1": build_health_result("p1", False),
        "p2": build_health_result("p2", False),
    }

    assert manager.pick_best_alternative(results) is None


def test_trigger_failover_updates_manager_state() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=3,
    )

    for _ in range(3):
        manager.record_active_profile_result(build_health_result("p1", False))

    event = manager.trigger_failover(
        "p3",
        reason="3 consecutive failures",
    )

    assert manager.active_profile_id == "p3"
    assert manager.consecutive_failures == 0
    assert event.from_profile_id == "p1"
    assert event.to_profile_id == "p3"
    assert event.reason == "3 consecutive failures"


def test_trigger_failover_records_events() -> None:
    manager = FailoverManager(active_profile_id="p1")

    manager.trigger_failover("p2", reason="first")
    manager.trigger_failover("p3", reason="second")

    assert len(manager.events) == 2
    assert manager.events[0].to_profile_id == "p2"
    assert manager.events[1].from_profile_id == "p2"
    assert manager.events[1].to_profile_id == "p3"


def test_service_record_calls_manager() -> None:
    service = FailoverService(initial_profile_id="p1")

    service.record(build_health_result("p1", True, 20.0))

    assert service.manager.consecutive_failures == 0


def test_service_should_trigger_after_threshold_failures() -> None:
    service = FailoverService(initial_profile_id="p1")

    for _ in range(service.manager.threshold):
        service.record(build_health_result("p1", False))

    assert service.should_trigger() is True


def test_service_pick_best_calls_manager() -> None:
    service = FailoverService(initial_profile_id="p1")

    results = {
        "p1": build_health_result("p1", False),
        "p2": build_health_result("p2", True, 30.0),
    }

    assert service.pick_best(results) == "p2"


def test_service_trigger_changes_active_profile() -> None:
    service = FailoverService(initial_profile_id="p1")

    service.trigger("p2", reason="manual switch")

    assert service.active_id == "p2"
    assert len(service.manager.events) == 1
    assert service.manager.events[0].reason == "manual switch"


def test_service_active_id_follows_manager() -> None:
    service = FailoverService(initial_profile_id="p1")

    assert service.active_id == "p1"

    service.trigger("p9", reason="test")

    assert service.active_id == "p9"


def test_best_alternative_is_deterministic_when_latencies_match() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p3": build_health_result("p3", True, 50.0),
        "p2": build_health_result("p2", True, 50.0),
    }

    assert manager.pick_best_alternative(results) == "p2"


def test_trigger_failover_returns_event() -> None:
    manager = FailoverManager(active_profile_id="p1")

    event = manager.trigger_failover("p2", reason="manual")

    assert event.from_profile_id == "p1"
    assert event.to_profile_id == "p2"
    assert manager.active_profile_id == "p2"


def test_failure_counter_does_not_change_for_other_profile() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=2,
    )

    manager.record_active_profile_result(build_health_result("p2", False))

    assert manager.consecutive_failures == 0
    assert manager.should_failover() is False


def test_success_after_threshold_failure_cancels_failover() -> None:
    manager = FailoverManager(
        active_profile_id="p1",
        consecutive_failure_threshold=2,
    )

    manager.record_active_profile_result(build_health_result("p1", False))
    manager.record_active_profile_result(build_health_result("p1", False))

    assert manager.should_failover() is True

    manager.record_active_profile_result(build_health_result("p1", True, 20.0))

    assert manager.consecutive_failures == 0
    assert manager.should_failover() is False


def test_no_failover_target_when_only_active_profile_is_healthy() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p1": build_health_result("p1", True, 10.0),
    }

    assert manager.pick_best_alternative(results) is None


def test_manager_rejects_empty_active_profile() -> None:
    import pytest

    with pytest.raises(ValueError, match="active_profile_id"):
        FailoverManager(active_profile_id="")


def test_manager_rejects_invalid_threshold() -> None:
    import pytest

    with pytest.raises(ValueError, match="at least 1"):
        FailoverManager(
            active_profile_id="p1",
            consecutive_failure_threshold=0,
        )


def test_trigger_failover_rejects_same_profile() -> None:
    import pytest

    manager = FailoverManager(active_profile_id="p1")

    with pytest.raises(ValueError, match="active profile"):
        manager.trigger_failover(
            "p1",
            reason="invalid",
        )


def test_best_alternative_uses_profile_id_as_deterministic_tiebreaker() -> None:
    manager = FailoverManager(active_profile_id="p1")

    results = {
        "p3": build_health_result("p3", True, 50.0),
        "p2": build_health_result("p2", True, 50.0),
    }

    assert manager.pick_best_alternative(results) == "p2"
