"""Tests for bimarz.subscription.

هیچ وابستگی خارجی (شبکه، رمزنگاری) ندارد — پارس کردن یک لینک متنی است.

No external dependency (network, crypto) — this is plain-text link
parsing.
"""

from __future__ import annotations

import pytest
from bimarz.subscription import MalformedLinkError, UnsupportedLinkError, parse_vless_link

_VALID_LINK = (
    "vless://8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d@example.com:443"
    "?encryption=none&flow=xtls-rprx-vision&security=reality"
    "&sni=www.microsoft.com&fp=chrome&pbk=abcDEF123&sid=a1b2c3&spx=%2F&type=tcp"
    "#My%20Test%20Server"
)


def test_parses_a_valid_vless_reality_link() -> None:
    result = parse_vless_link(_VALID_LINK)
    assert result.uuid == "8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d"
    assert result.address == "example.com"
    assert result.port == 443
    assert result.flow == "xtls-rprx-vision"
    assert result.security == "reality"
    assert result.sni == "www.microsoft.com"
    assert result.fingerprint == "chrome"
    assert result.public_key == "abcDEF123"
    assert result.short_id == "a1b2c3"
    assert result.spider_x == "/"
    assert result.network == "tcp"
    assert result.remark == "My Test Server"


def test_falls_back_to_hostname_when_no_remark_fragment() -> None:
    link = _VALID_LINK.split("#")[0]
    result = parse_vless_link(link)
    assert result.remark == "example.com"


def test_rejects_non_vless_scheme() -> None:
    with pytest.raises(UnsupportedLinkError):
        parse_vless_link("vmess://something")


def test_rejects_invalid_uuid() -> None:
    with pytest.raises(MalformedLinkError):
        parse_vless_link("vless://not-a-uuid@example.com:443?security=reality&flow=xtls-rprx-vision&pbk=x")


def test_rejects_missing_host() -> None:
    with pytest.raises(MalformedLinkError):
        parse_vless_link("vless://8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d@:443?security=reality")


def test_rejects_non_reality_security() -> None:
    with pytest.raises(UnsupportedLinkError):
        parse_vless_link(
            "vless://8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d@example.com:443?security=tls&flow=xtls-rprx-vision&pbk=x"
        )


def test_rejects_non_vision_flow() -> None:
    with pytest.raises(UnsupportedLinkError):
        parse_vless_link(
            "vless://8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d@example.com:443?security=reality&flow=none&pbk=x"
        )


def test_rejects_missing_public_key() -> None:
    with pytest.raises(MalformedLinkError):
        parse_vless_link(
            "vless://8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d@example.com:443?security=reality&flow=xtls-rprx-vision"
        )
