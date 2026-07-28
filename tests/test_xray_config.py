"""Tests for bimarz.xray_config.

Pure string/dict generation — no subprocess, no network, no crypto.

تست‌های bimarz.xray_config.

فقط تولید رشته/دیکشنری — بدون subprocess، بدون شبکه، بدون رمزنگاری.
"""

from __future__ import annotations

import json

from bimarz.xray_config import build_connect_config


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


def test_stats_and_policy_sections_present_for_get_stats_to_work() -> None:
    config = json.loads(build_connect_config())
    assert "stats" in config
    assert config["policy"]["system"]["statsOutboundUplink"] is True
    assert config["policy"]["system"]["statsOutboundDownlink"] is True
