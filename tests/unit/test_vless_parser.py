"""Unit tests for the VLESS share-link parser."""
# تست‌های واحد برای پارسر لینک اشتراک VLESS

from __future__ import annotations

import pytest
from bimarz.parsers.vless import (
    MalformedVlessError,
    UnsupportedVlessError,
    VlessParseError,
    parse_vless_link,
)

# A stable UUID used by all parser test cases.
# یک UUID ثابت برای تمام تست‌های پارسر.
VALID_UUID = "11111111-1111-4111-8111-111111111111"

# A stable Reality public key used by valid parser fixtures.
# یک کلید عمومی ثابت Reality برای fixtureهای معتبر پارسر.
PUBLIC_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"

# A well-formed VLESS Reality Vision URI used as the baseline fixture.
# یک URI معتبر VLESS Reality Vision به عنوان fixture پایه.
VALID_VLESS_LINK = (
    f"vless://{VALID_UUID}@example.com:443"
    "?type=tcp"
    "&security=reality"
    "&flow=xtls-rprx-vision"
    f"&pbk={PUBLIC_KEY}"
    "&sni=example.com"
    "#test-profile"
)


def test_parse_valid_vless_link() -> None:
    """Parse a valid VLESS Reality Vision URI into a ServerProfile."""
    # یک URI معتبر VLESS Reality Vision را به ServerProfile تبدیل می‌کند.
    result = parse_vless_link(VALID_VLESS_LINK)

    assert result.remark == "test-profile"
    assert result.outbound_config["protocol"] == "vless"
    assert result.outbound_config["address"] == "example.com"
    assert result.outbound_config["port"] == 443
    assert result.outbound_config["id"] == VALID_UUID
    assert result.outbound_config["security"] == "reality"
    assert result.outbound_config["flow"] == "xtls-rprx-vision"
    assert result.outbound_config["publicKey"] == PUBLIC_KEY
    assert result.outbound_config["sni"] == "example.com"


def test_parse_vless_preserves_query_parameters() -> None:
    """Preserve supported VLESS query parameters."""
    # پارامترهای پشتیبانی‌شده VLESS باید بدون تغییر حفظ شوند.
    result = parse_vless_link(VALID_VLESS_LINK)
    outbound = result.outbound_config

    assert outbound["type"] == "tcp"
    assert outbound["security"] == "reality"
    assert outbound["flow"] == "xtls-rprx-vision"
    assert outbound["publicKey"] == PUBLIC_KEY
    assert outbound["sni"] == "example.com"
    assert outbound["fp"] == "chrome"
    assert outbound["encryption"] == "none"


@pytest.mark.parametrize(
    "link",
    [
        "",
        "vless://",
        f"vless://@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}",
        f"vless://not-a-uuid@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}",
    ],
)
def test_malformed_vless_links_are_rejected(link: str) -> None:
    """Reject malformed VLESS URIs."""
    # URIهای ناقص یا دارای ساختار نامعتبر VLESS باید رد شوند.
    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_scheme_less_link_is_rejected() -> None:
    """Reject bare text without a vless scheme."""
    # متن بدون scheme مربوط به VLESS باید رد شود.
    with pytest.raises(UnsupportedVlessError):
        parse_vless_link("invalid")


@pytest.mark.parametrize(
    "link",
    [
        "http://example.com",
        f"vmess://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}",
    ],
)
def test_unsupported_scheme_is_rejected(link: str) -> None:
    """Reject non-vless schemes as unsupported."""
    # schemeهای غیر VLESS باید به عنوان پشتیبانی‌نشده رد شوند.
    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_rejects_non_reality_security() -> None:
    """Reject security values other than reality."""
    # هر security غیر از reality باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=tls&flow=xtls-rprx-vision&pbk=pk"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_rejects_non_vision_flow() -> None:
    """Reject flow values other than xtls-rprx-vision."""
    # هر flow غیر از xtls-rprx-vision باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&flow=none&pbk=pk"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_rejects_missing_public_key() -> None:
    """Reject Reality links that omit pbk."""
    # لینک Reality بدون pbk باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-vision"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_rejects_missing_security() -> None:
    """Reject links that omit security=reality."""
    # لینک بدون security=reality باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_rejects_missing_flow() -> None:
    """Reject links that omit the required Vision flow."""
    # لینک بدون flow مربوط به Vision باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_spider_x_and_short_id_preserved() -> None:
    """Preserve sid and spx parameters."""
    # پارامترهای sid و spx باید حفظ شوند.
    link = (
        f"vless://{VALID_UUID}@example.com:443"
        "?security=reality"
        "&flow=xtls-rprx-vision"
        f"&pbk={PUBLIC_KEY}"
        "&sid=a1b2"
        "&spx=%2Fpath"
    )

    result = parse_vless_link(link)
    outbound = result.outbound_config

    assert outbound["shortId"] == "a1b2"
    assert outbound["spiderX"] == "/path"


def test_parse_errors_are_value_error_subclasses() -> None:
    """Ensure parse errors remain compatible with ValueError handlers."""
    # خطاهای پارس باید زیرکلاس ValueError بمانند تا با handlerهای موجود سازگار باشند.
    assert issubclass(VlessParseError, ValueError)
    assert issubclass(MalformedVlessError, VlessParseError)
    assert issubclass(UnsupportedVlessError, VlessParseError)


def test_parse_vless_uses_default_port() -> None:
    """Use port 443 when the URI does not specify a port."""
    # اگر پورت مشخص نشده باشد، پورت پیش‌فرض 443 استفاده می‌شود.
    link = f"vless://{VALID_UUID}@example.com?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

    assert result.outbound_config["address"] == "example.com"
    assert result.outbound_config["port"] == 443
    assert result.remark == "example.com:443"


def test_parse_vless_without_fragment() -> None:
    """Generate a fallback profile name when the fragment is absent."""
    # در نبود fragment باید یک نام جایگزین برای پروفایل ساخته شود.
    link = f"vless://{VALID_UUID}@127.0.0.1:8443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

    assert result.outbound_config["address"] == "127.0.0.1"
    assert result.outbound_config["port"] == 8443
    assert result.remark == "127.0.0.1:8443"


def test_parse_vless_decodes_fragment() -> None:
    """Decode URL-encoded profile names."""
    # نام URL-encoded پروفایل باید به متن اصلی تبدیل شود.
    link = (
        f"vless://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}#test%20profile"
    )

    result = parse_vless_link(link)

    assert result.remark == "test profile"


def test_parse_vless_decodes_query_values() -> None:
    """Decode URL-encoded query parameter values."""
    # مقادیر URL-encoded پارامترهای query باید decode شوند.
    link = (
        f"vless://{VALID_UUID}@example.com:443"
        "?security=reality"
        "&flow=xtls-rprx-vision"
        f"&pbk={PUBLIC_KEY}"
        "&sni=server%2Eexample%2Ecom"
        "&path=%2Fapi%2Fvless"
    )

    result = parse_vless_link(link)
    outbound = result.outbound_config

    assert outbound["sni"] == "server.example.com"
    assert outbound["path"] == "/api/vless"


def test_parse_vless_uses_host_as_sni_fallback() -> None:
    """Use host as the SNI fallback when sni is absent."""
    # در نبود sni باید مقدار host به عنوان SNI استفاده شود.
    link = (
        f"vless://{VALID_UUID}@example.com:443"
        "?security=reality"
        "&flow=xtls-rprx-vision"
        f"&pbk={PUBLIC_KEY}"
        "&host=server.example.com"
    )

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
        (
            f"vless://{VALID_UUID}@example.com:1?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}",
            1,
        ),
        (VALID_VLESS_LINK, 443),
        (
            f"vless://{VALID_UUID}@example.com:65535?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}",
            65535,
        ),
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
        (f"vless://{VALID_UUID}@example.com:0?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"),
        (f"vless://{VALID_UUID}@example.com:65536?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"),
        (f"vless://{VALID_UUID}@example.com:not-a-port?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"),
    ],
)
def test_parse_vless_rejects_invalid_ports(link: str) -> None:
    """Reject invalid port values."""
    # مقادیر نامعتبر پورت باید با خطای اعتبارسنجی رد شوند.
    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_parse_vless_normalizes_uuid() -> None:
    """Normalize a valid UUID to its canonical string representation."""
    # UUID معتبر باید به قالب استاندارد خود نرمال شود.
    uppercase_uuid = VALID_UUID.upper()
    link = f"vless://{uppercase_uuid}@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

    assert result.outbound_config["id"] == VALID_UUID
