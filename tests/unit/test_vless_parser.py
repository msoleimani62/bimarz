from __future__ import annotations

import pytest
from bimarz.parsers.vless import (
    MalformedVlessError,
    UnsupportedVlessError,
    parse_vless_link,
)

VALID_UUID = "11111111-1111-4111-8111-111111111111"
PUBLIC_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
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


def test_parse_vless_uses_default_port() -> None:
    """Use port 443 when the URI does not specify a port."""
    # اگر پورت مشخص نشده باشد، پورت پیش‌فرض 443 استفاده می‌شود.
    link = f"vless://{VALID_UUID}@example.com?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

    assert result.outbound_config["port"] == 443


def test_parse_vless_without_fragment() -> None:
    """Generate a fallback profile name when the fragment is absent."""
    # در نبود fragment باید یک نام جایگزین برای پروفایل ساخته شود.
    link = f"vless://{VALID_UUID}@127.0.0.1:8443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

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

    assert result.outbound_config["sni"] == "server.example.com"
    assert result.outbound_config["path"] == "/api/vless"


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

    assert result.outbound_config["sni"] == "server.example.com"


def test_parse_vless_generates_unique_profile_ids() -> None:
    """Generate unique profile IDs for repeated parsing."""
    # هر بار پارس کردن باید یک profile_id یکتا تولید کند.
    first = parse_vless_link(VALID_VLESS_LINK)
    second = parse_vless_link(VALID_VLESS_LINK)

    assert first.profile_id != second.profile_id
    assert first.tag != second.tag


@pytest.mark.parametrize(
    ("link", "expected_port"),
    [
        (
            (f"vless://{VALID_UUID}@example.com:1?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"),
            1,
        ),
        (VALID_VLESS_LINK, 443),
        (
            (f"vless://{VALID_UUID}@example.com:65535?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"),
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


def test_parse_vless_normalizes_uuid() -> None:
    """Normalize a valid UUID to its canonical string representation."""
    # UUID معتبر باید به قالب استاندارد خود نرمال شود.
    uppercase_uuid = VALID_UUID.upper()
    link = f"vless://{uppercase_uuid}@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    result = parse_vless_link(link)

    assert result.outbound_config["id"] == VALID_UUID


def test_parse_vless_rejects_empty_link() -> None:
    """Reject an empty VLESS link."""
    # لینک خالی VLESS باید رد شود.
    with pytest.raises(MalformedVlessError):
        parse_vless_link("")


def test_parse_vless_rejects_missing_uuid() -> None:
    """Reject a VLESS link without a UUID."""
    # لینک VLESS بدون UUID باید رد شود.
    link = f"vless://@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_invalid_uuid() -> None:
    """Reject an invalid UUID."""
    # UUID نامعتبر باید رد شود.
    link = f"vless://not-a-uuid@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_unsupported_scheme() -> None:
    """Reject non-VLESS URI schemes."""
    # scheme غیر VLESS باید رد شود.
    link = f"vmess://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_missing_security() -> None:
    """Reject links without Reality security."""
    # لینک بدون security=reality باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_unsupported_security() -> None:
    """Reject VLESS links using unsupported security."""
    # security غیر Reality باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=tls&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_missing_flow() -> None:
    """Reject links without Vision flow."""
    # لینک بدون flow مربوط به Vision باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_unsupported_flow() -> None:
    """Reject links using an unsupported VLESS flow."""
    # flow غیر xtls-rprx-vision باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-direct&pbk={PUBLIC_KEY}"

    with pytest.raises(UnsupportedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_missing_public_key() -> None:
    """Reject Reality links without a public key."""
    # لینک Reality بدون public key باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:443?security=reality&flow=xtls-rprx-vision"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


@pytest.mark.parametrize(
    "port",
    ["0", "65536"],
)
def test_parse_vless_rejects_invalid_port(port: str) -> None:
    """Reject ports outside the valid TCP range."""
    # پورت خارج از بازه معتبر TCP باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:{port}?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)


def test_parse_vless_rejects_invalid_port_syntax() -> None:
    """Reject malformed port values."""
    # مقدار نحوی نامعتبر پورت باید رد شود.
    link = f"vless://{VALID_UUID}@example.com:not-a-port?security=reality&flow=xtls-rprx-vision&pbk={PUBLIC_KEY}"

    with pytest.raises(MalformedVlessError):
        parse_vless_link(link)
