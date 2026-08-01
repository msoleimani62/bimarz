"""Tests for bimarz.dns_leak_guard.

Pure dict generation tests — no network needed.

تست‌های bimarz.dns_leak_guard.

فقط تست تولید دیکشنری — بدون شبکه.
"""

from __future__ import annotations

from bimarz.dns_leak_guard import get_default_dns_guard_config, get_dns_routing_rule


def test_dns_config_contains_doh_server() -> None:
    config = get_default_dns_guard_config()
    assert "1.1.1.1" in config["servers"][0]
    assert config["queryStrategy"] == "UseIP"


def test_dns_routing_rule_targets_port_53() -> None:
    rule = get_dns_routing_rule()
    assert rule["port"] == "53"
    assert "dns-out" in rule["outboundTag"]
