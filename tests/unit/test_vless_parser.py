"""Unit tests for the VLESS share-link parser."""
# تست‌های واحد برای پارسر لینک اشتراک VLESS

from __future__ import annotations

import pytest
from bimarz.parsers.vless import parse_vless_link

# A stable UUID used by all parser test cases.
# یک UUID ثابت برای تمام تست‌های پارسر.
VALID_UUID = "11111111-1111-4111-8111-111111111111"


# A well-formed VLESS URI used as the baseline test fixture.
# یک URI معتبر VLESS به عنوان نمونه پایه تست‌ها.
VALID_VLESS_LINK = f"vless://{VALID_UUID}@example.com:443?type=tcp&security=reality&sni=example.com#test-profile"


def test_parse_valid_vless_link() -> None:
    """Parse a valid VLESS URI into a ServerProfile."""
    # یک URI معتبر VLESS را به ServerProfile تبدیل می‌کند.
    result = parse_vless_link(VALID_VLESS_LINK)

    assert result.outbound_config["protocol"] == "vless"
    assert result.outbound_config["id"] == VALID_UUID
    assert result.outbound_config["address"] == "example.com"
    assert result.outbound_config["port"] == 443
    assert result.remark == "test-profile"


def test_parse_vless_preserves_query_parameters() -> None:
    """Preserve supported VLESS query parameters."""
    # پارامترهای پشتیبانی‌شده VLESS باید بدون تغییر حفظ شوند.
    result = parse_vless_link(VALID_VLESS_LINK)
    outbound = result.outbound_config

    assert outbound["type"] == "tcp"
    assert outbound["security"] == "reality"
    assert outbound["sni"] == "example.com"


@pytest.mark.parametrize(
    "link",
    [
        "",
        "invalid",
        "http://example.com",
        "vless://",
        "vless://@example.com:443",
        "vless://not-a-uuid@example.com:443",
    ],
)
def test_invalid_vless_links_are_rejected(link: str) -> None:
    """Reject malformed or unsupported VLESS URIs."""
    # URIهای ناقص، نامعتبر یا پشتیبانی‌نشده VLESS باید رد شوند.
    with pytest.raises(ValueError):
        parse_vless_link(link)


def test_parse_vless_uses_default_port() -> None:
    """Use port 443 when the URI does not specify a port."""
    # اگر پورت مشخص نشده باشد، پورت پیش‌فرض 443 استفاده می‌شود.
    link = f"vless://{VALID_UUID}@example.com"

    result = parse_vless_link(link)

    assert result.outbound_config["address"] == "example.com"
    assert result.outbound_config["port"] == 443
    assert result.remark == "example.com:443"


def test_parse_vless_without_fragment() -> None:
    """Generate a fallback profile name when the fragment is absent."""
    # در نبود fragment باید یک نام جایگزین برای پروفایل ساخته شود.
    link = f"vless://{VALID_UUID}@127.0.0.1:8443"

    result = parse_vless_link(link)

    assert result.outbound_config["address"] == "127.0.0.1"
    assert result.outbound_config["port"] == 8443
    assert result.remark == "127.0.0.1:8443"


def test_parse_vless_decodes_fragment() -> None:
    """Decode URL-encoded profile names."""
    # نام URL-encoded پروفایل باید به متن اصلی تبدیل شود.
    link = f"vless://{VALID_UUID}@example.com:443#test%20profile"

    result = parse_vless_link(link)

    assert result.remark == "test profile"


def test_parse_vless_decodes_query_values() -> None:
    """Decode URL-encoded query parameter values."""
    # مقادیر URL-encoded پارامترهای query باید decode شوند.
    link = f"vless://{VALID_UUID}@example.com:443?sni=server%2Eexample%2Ecom&path=%2Fapi%2Fvless"

    result = parse_vless_link(link)
    outbound = result.outbound_config

    assert outbound["sni"] == "server.example.com"
    assert outbound["path"] == "/api/vless"


def test_parse_vless_uses_host_as_sni_fallback() -> None:
    """Use host as the SNI fallback when sni is absent."""
    # در نبود sni باید مقدار host به عنوان SNI استفاده شود.
    link = f"vless://{VALID_UUID}@example.com:443?host=server.example.com"

    result = parse_vless_link(link)

    assert result.outbound_config["host"] == "server.example.com"
    assert result.outbound_config["sni"] == "server.example.com"


def test_parse_vless_generates_unique_profile_ids() -> None:
    """Generate unique profile IDs for repeated parsing."""
    # هر بار پارس کردن باید یک profile_id یکتا تولید کند.
    first = parse_vless_link(VALID_VLESS_LINK)
    second = parse_vless_link(VALID_VLESS_LINK)

    assert first.profile_id != second.profile_id
    assert first.tag != second.tag
    assert first.profile_id == first.tag
    assert second.profile_id == second.tag


@pytest.mark.parametrize(
    ("link", "expected_port"),
    [
        (f"vless://{VALID_UUID}@example.com:1", 1),
        (f"vless://{VALID_UUID}@example.com:443", 443),
        (f"vless://{VALID_UUID}@example.com:65535", 65535),
    ],
)
def test_parse_vless_accepts_valid_port_range(
    link: str,
    expected_port: int,
) -> None:
    """Accept valid TCP port values."""
    # مقادیر معتبر بازه پورت TCP باید پذیرفته شوند.
    result = parse_vless_link(link)

    assert result.outbound_config["port"] == expected_port


@pytest.mark.parametrize(
    "link",
    [
        f"vless://{VALID_UUID}@example.com:0",
        f"vless://{VALID_UUID}@example.com:65536",
        f"vless://{VALID_UUID}@example.com:not-a-port",
    ],
)
def test_parse_vless_rejects_invalid_ports(link: str) -> None:
    """Reject invalid port values."""
    # مقادیر نامعتبر پورت باید با ValueError رد شوند.
    with pytest.raises(ValueError):
        parse_vless_link(link)


def test_parse_vless_normalizes_uuid() -> None:
    """Normalize a valid UUID to its canonical string representation."""
    # UUID معتبر باید به قالب استاندارد خود نرمال شود.
    uppercase_uuid = VALID_UUID.upper()
    link = f"vless://{uppercase_uuid}@example.com:443"

    result = parse_vless_link(link)

    assert result.outbound_config["id"] == VALID_UUID
