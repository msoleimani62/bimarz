"""Parsing vless:// share links into a structured VlessRealityOutbound.

Deliberately supports ONLY VLESS + Reality + Vision — the exact
combination this project's roadmap targets. Any other protocol or
security type is rejected with a clear error rather than silently
producing a broken/incomplete outbound config, since a half-parsed
config that xray-core then rejects (or worse, silently mis-routes
traffic on) is far more dangerous than an upfront refusal.

پارس کردن لینک‌های اشتراک vless:// به یک VlessRealityOutbound ساختاریافته.

عمداً فقط VLESS + Reality + Vision را پشتیبانی می‌کند — دقیقاً همان
ترکیبی که نقشه راه این پروژه هدف گرفته. هر پروتکل یا نوع امنیتی دیگری با
یک خطای واضح رد می‌شود، نه اینکه بی‌صدا یک outbound ناقص/شکسته تولید
کند — چون یک کانفیگ نصفه‌کاره که بعداً xray-core ردش می‌کند (یا بدتر،
بی‌صدا ترافیک را غلط مسیر‌دهی می‌کند) بسیار خطرناک‌تر از یک رد صریح
همان ابتدا است.
"""

from __future__ import annotations

import uuid as uuid_module
from urllib.parse import parse_qs, unquote, urlparse

from bimarz.models import VlessRealityOutbound


class SubscriptionParseError(Exception):
    """Base class for every subscription/link parsing error.

    کلاس پایه برای تمام خطاهای پارس لینک/subscription.
    """


class UnsupportedLinkError(SubscriptionParseError):
    """Raised when a link is syntactically valid but uses a
    protocol/security/flow combination this project does not support.

    زمانی پرتاب می‌شود که لینک از نظر نحوی معتبر است ولی از ترکیب
    پروتکل/امنیت/flow ای استفاده می‌کند که این پروژه پشتیبانی نمی‌کند.
    """


class MalformedLinkError(SubscriptionParseError):
    """Raised when a vless:// link is missing a required field or has an
    invalid value in a field it does have.

    زمانی پرتاب می‌شود که یک لینک vless:// فاقد یک فیلد ضروری است یا
    مقدار نامعتبری در فیلدی که دارد وجود دارد.
    """


def parse_vless_link(link: str) -> VlessRealityOutbound:
    """Parses a single vless:// share link into a VlessRealityOutbound.

    یک لینک اشتراک vless:// را به یک VlessRealityOutbound پارس می‌کند.
    """
    link = link.strip()
    parsed = urlparse(link)

    if parsed.scheme != "vless":
        raise UnsupportedLinkError(f"expected a vless:// link, got scheme '{parsed.scheme or '(none)'}'")

    if not parsed.username:
        raise MalformedLinkError("vless link is missing the UUID (userinfo) part")
    try:
        user_uuid = str(uuid_module.UUID(parsed.username))
    except ValueError as exc:
        raise MalformedLinkError(f"invalid UUID in vless link: {parsed.username!r}") from exc

    if not parsed.hostname:
        raise MalformedLinkError("vless link is missing a host")
    if not parsed.port:
        raise MalformedLinkError("vless link is missing a port")

    query = parse_qs(parsed.query)

    def get(key: str, default: str = "") -> str:
        values = query.get(key)
        return values[0] if values else default

    security = get("security").lower()
    if security != "reality":
        raise UnsupportedLinkError(f"only security=reality is supported by this project, got '{security or '(none)'}'")

    flow = get("flow")
    if flow != "xtls-rprx-vision":
        raise UnsupportedLinkError(f"only flow=xtls-rprx-vision is supported by this project, got '{flow or '(none)'}'")

    public_key = get("pbk")
    if not public_key:
        raise MalformedLinkError("vless+reality link is missing the 'pbk' (Reality public key) parameter")

    remark = unquote(parsed.fragment) if parsed.fragment else parsed.hostname

    return VlessRealityOutbound(
        uuid=user_uuid,
        address=parsed.hostname,
        port=parsed.port,
        flow=flow,
        network=get("type", "tcp"),
        security=security,
        sni=get("sni"),
        fingerprint=get("fp", "chrome"),
        public_key=public_key,
        short_id=get("sid"),
        spider_x=get("spx"),
        remark=remark,
    )
