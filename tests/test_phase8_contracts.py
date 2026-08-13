"""
Phase 8 contract tests.

Guarantees cross-module invariants required for a correct connection
lifecycle, without requiring the native extension.

تست‌های قرارداد فاز ۸.

invariantهای بین‌ماژولی لازم برای چرخه اتصال صحیح را تضمین می‌کند،
بدون نیاز به extension native.
"""

from __future__ import annotations

import json

from bimarz.helpers import outbound_kwargs
from bimarz.models import ServerProfile

from bimarz import constants, xray_config


def _profile() -> ServerProfile:
    return ServerProfile(
        profile_id="p1",
        tag="p1",
        remark="Test",
        outbound_config={
            "id": "11111111-1111-1111-1111-111111111111",
            "address": "example.com",
            "port": 443,
            "type": "tcp",
            "sni": "example.com",
            "fp": "chrome",
            "publicKey": "dGVzdA==",
            "shortId": "abcd",
            "flow": "xtls-rprx-vision",
        },
        added_at_iso="2026-08-12T00:00:00+00:00",
    )


def test_active_outbound_tag_has_single_canonical_value() -> None:
    """All outbound-related modules must share one canonical tag.

    همه ماژول‌های مرتبط با outbound باید یک تگ canonical مشترک داشته باشند.
    """
    assert constants.ACTIVE_OUTBOUND_TAG == "bimarz-active"
    assert xray_config.ACTIVE_OUTBOUND_TAG == constants.ACTIVE_OUTBOUND_TAG


def test_routing_outbound_tag_matches_helper_outbound_tag() -> None:
    """SOCKS routing must target the tag used by outbound creation.

    routing مربوط به SOCKS باید همان تگ ساخت outbound را هدف بگیرد.
    """
    config = json.loads(xray_config.build_connect_config())
    rules = config["routing"]["rules"]

    socks_rules = [rule for rule in rules if rule.get("inboundTag") == ["socks-in"]]

    assert len(socks_rules) == 1

    kwargs = outbound_kwargs(_profile())

    assert socks_rules[0]["outboundTag"] == constants.ACTIVE_OUTBOUND_TAG
    assert kwargs["tag"] == constants.ACTIVE_OUTBOUND_TAG


def test_xray_config_reexports_canonical_tag() -> None:
    """xray_config must expose the canonical constants import path.

    xray_config باید مقدار canonical موجود در constants را expose کند.
    """
    assert xray_config.ACTIVE_OUTBOUND_TAG == constants.ACTIVE_OUTBOUND_TAG
