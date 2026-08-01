"""Tests for bimarz.xray_config.

Pure string/dict generation — no subprocess, no network, no crypto.

تست‌های bimarz.xray_config.

فقط تولید رشته/دیکشنری — بدون subprocess، بدون شبکه، بدون رمزنگاری.
"""

from __future__ import annotations

import json

from bimarz.xray_config import ACTIVE_OUTBOUND_TAG, build_connect_config


def test_produces_valid_json() -> None:
    config = json.loads(build_connect_config())
    assert isinstance(config, dict)


def test_api_listens_on_the_given_grpc_endpoint() -> None:
    config = json.loads(build_connect_config(grpc_endpoint="http://127.0.0.1:12345"))
    assert config["api"]["listen"] == "127.0.0.1:12345"


def test_api_declares_handler_and_stats_services() -> None:
    config = json.loads(build_connect_config())
    assert "HandlerService" in config["api"]["services"]
    assert "StatsService" in config["api"]["services"]


def test_socks_inbound_uses_the_given_port() -> None:
    config = json.loads(build_connect_config(local_socks_port=9999))
    socks_inbounds = [i for i in config["inbounds"] if i["protocol"] == "socks"]
    assert len(socks_inbounds) == 1
    assert socks_inbounds[0]["port"] == 9999


def test_has_a_placeholder_outbound_so_xray_core_starts_cleanly() -> None:
    config = json.loads(build_connect_config())
    assert len(config["outbounds"]) >= 1
    assert config["outbounds"][0]["protocol"] == "freedom"


def test_routing_sends_socks_traffic_to_the_active_outbound_tag() -> None:
    config = json.loads(build_connect_config())
    rules = config["routing"]["rules"]
    socks_rules = [r for r in rules if r.get("inboundTag") == ["socks-in"]]
    assert len(socks_rules) == 1
    assert socks_rules[0]["outboundTag"] == ACTIVE_OUTBOUND_TAG


def test_stats_and_policy_sections_present_for_get_stats_to_work() -> None:
    config = json.loads(build_connect_config())
    assert "stats" in config
    assert config["policy"]["system"]["statsOutboundUplink"] is True
    assert config["policy"]["system"]["statsOutboundDownlink"] is True


def test_dns_guard_adds_dns_outbound_when_enabled() -> None:
    config = json.loads(build_connect_config(enable_dns_guard=True))
    dns_outbounds = [o for o in config["outbounds"] if o.get("tag") == "dns-out"]
    assert len(dns_outbounds) == 1
    assert dns_outbounds[0]["protocol"] == "dns"
    assert "dns" in config


def test_dns_guard_adds_routing_rule_for_port_53() -> None:
    config = json.loads(build_connect_config(enable_dns_guard=True))
    dns_rules = [r for r in config["routing"]["rules"] if r.get("port") == "53"]
    assert len(dns_rules) == 1
    assert dns_rules[0]["outboundTag"] == "dns-out"


def test_dns_guard_can_be_disabled() -> None:
    config = json.loads(build_connect_config(enable_dns_guard=False))
    assert "dns" not in config
    dns_outbounds = [o for o in config["outbounds"] if o.get("tag") == "dns-out"]
    assert len(dns_outbounds) == 0
