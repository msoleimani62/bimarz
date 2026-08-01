"""Tests for bimarz.failover.FailoverManager.

Pure decision-logic tests — no network, no Rust extension needed, since
FailoverManager never touches the network itself (it only processes
HealthCheckResult values handed to it).

تست‌های bimarz.failover.FailoverManager.

فقط تست منطق تصمیم‌گیری — بدون شبکه، بدون نیاز به ماژول Rust، چون
FailoverManager هرگز خودش با شبکه کار نمی‌کند (فقط مقادیر HealthCheckResult
که بهش داده می‌شه رو پردازش می‌کنه).
"""

from __future__ import annotations

from bimarz.failover import FailoverManager
from bimarz.models import HealthCheckResult


def _result(profile_id: str, reachable: bool, latency_ms: float | None = None) -> HealthCheckResult:
    return HealthCheckResult(
        profile_id=profile_id,
        reachable=reachable,
        latency_ms=latency_ms,
        checked_at_iso="2026-07-28T00:00:00+00:00",
        error_message=None if reachable else "unreachable",
    )


def test_healthy_result_keeps_failure_count_at_zero() -> None:
    manager = FailoverManager(active_profile_id="p1")
    manager.record_active_profile_result(_result("p1", True, 50.0))
    assert manager.consecutive_failures == 0
    assert manager.should_failover() is False


def test_failures_below_threshold_do_not_trigger_failover() -> None:
    manager = FailoverManager(active_profile_id="p1", consecutive_failure_threshold=3)
    manager.record_active_profile_result(_result("p1", False))
    manager.record_active_profile_result(_result("p1", False))
    assert manager.consecutive_failures == 2
    assert manager.should_failover() is False


def test_reaching_the_threshold_triggers_failover() -> None:
    manager = FailoverManager(active_profile_id="p1", consecutive_failure_threshold=3)
    for _ in range(3):
        manager.record_active_profile_result(_result("p1", False))
    assert manager.should_failover() is True


def test_a_healthy_result_resets_the_counter_after_failures() -> None:
    manager = FailoverManager(active_profile_id="p1", consecutive_failure_threshold=3)
    manager.record_active_profile_result(_result("p1", False))
    manager.record_active_profile_result(_result("p1", False))
    manager.record_active_profile_result(_result("p1", True, 30.0))
    assert manager.consecutive_failures == 0


def test_results_for_other_profiles_are_ignored() -> None:
    manager = FailoverManager(active_profile_id="p1", consecutive_failure_threshold=3)
    manager.record_active_profile_result(_result("p1", False))
    manager.record_active_profile_result(_result("p2", True, 10.0))
    assert manager.consecutive_failures == 1


def test_pick_best_alternative_returns_lowest_latency_reachable_profile() -> None:
    manager = FailoverManager(active_profile_id="p1")
    all_results = {
        "p1": _result("p1", False),
        "p2": _result("p2", True, 120.0),
        "p3": _result("p3", True, 45.0),
        "p4": _result("p4", False),
    }
    assert manager.pick_best_alternative(all_results) == "p3"


def test_pick_best_alternative_excludes_the_active_profile_even_if_reachable() -> None:
    manager = FailoverManager(active_profile_id="p1")
    all_results = {"p1": _result("p1", True, 1.0), "p2": _result("p2", True, 999.0)}
    assert manager.pick_best_alternative(all_results) == "p2"


def test_pick_best_alternative_returns_none_when_nothing_reachable() -> None:
    manager = FailoverManager(active_profile_id="p1")
    all_results = {"p1": _result("p1", False), "p2": _result("p2", False)}
    assert manager.pick_best_alternative(all_results) is None


def test_trigger_failover_updates_active_profile_and_resets_counter() -> None:
    manager = FailoverManager(active_profile_id="p1", consecutive_failure_threshold=3)
    for _ in range(3):
        manager.record_active_profile_result(_result("p1", False))

    event = manager.trigger_failover("p3", reason="3 consecutive failures")

    assert manager.active_profile_id == "p3"
    assert manager.consecutive_failures == 0
    assert event.from_profile_id == "p1"
    assert event.to_profile_id == "p3"
    assert event.reason == "3 consecutive failures"


def test_trigger_failover_appends_to_the_events_log() -> None:
    manager = FailoverManager(active_profile_id="p1")
    manager.trigger_failover("p2", reason="test")
    manager.trigger_failover("p3", reason="test again")
    assert len(manager.events) == 2
    assert manager.events[0].to_profile_id == "p2"
    assert manager.events[1].from_profile_id == "p2"
    assert manager.events[1].to_profile_id == "p3"
