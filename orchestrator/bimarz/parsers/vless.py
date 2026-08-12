"""
Canonical VLESS share-link parser.

Produces a ServerProfile for the rest of the application
(ProfileService, ProfileStore, CLI, GUI, health-check, failover, engine).

Contract for Phase 7:
  protocol = vless
  security = reality
  flow     = xtls-rprx-vision
  pbk      required

پارسر رسمی لینک اشتراک VLESS.

خروجی ServerProfile برای بقیه سیستم است.
قرارداد فاز 7: VLESS + Reality + Vision با pbk اجباری.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TypedDict
from urllib.parse import parse_qs, unquote, urlparse

from bimarz.models import ServerProfile

# Required Reality + Vision values for BiMarz Phase 7 profiles.
# مقادیر اجباری Reality و Vision برای پروفایل‌های فاز 7 BiMarz.
REQUIRED_SECURITY = "reality"
REQUIRED_FLOW = "xtls-rprx-vision"

DEFAULT_PORT = 443
DEFAULT_FINGERPRINT = "chrome"
DEFAULT_NETWORK = "tcp"
DEFAULT_ENCRYPTION = "none"


class VlessParseError(ValueError):
    """Base class for every VLESS share-link parse failure.

    کلاس پایه برای تمام خطاهای پارس لینک VLESS.
    """


class UnsupportedVlessError(VlessParseError):
    """Link is syntactically usable but uses an unsupported combination.

    لینک از نظر نحوی قابل استفاده است ولی ترکیب پشتیبانی‌نشده دارد.
    """


class MalformedVlessError(VlessParseError):
    """Link is missing a required field or has an invalid value.

    لینک فاقد فیلد ضروری است یا مقدار نامعتبر دارد.
    """


class VlessOutbound(TypedDict, total=False):
    protocol: str
    address: str
    port: int
    id: str
    flow: str
    security: str
    sni: str
    fp: str
    publicKey: str
    shortId: str
    spiderX: str
    encryption: str
    type: str
    path: str
    host: str
    serviceName: str
    authority: str
    mode: str
    alpn: str
    headerType: str
    seed: str
    packetEncoding: str
    mux: str
    allowInsecure: bool
    ech: str
    echForceQuery: str
    pqv: str


def parse_vless_link(link: str) -> ServerProfile:
    """Parse a VLESS share link into a validated ServerProfile.

    یک لینک اشتراک VLESS را به ServerProfile اعتبارسنجی‌شده تبدیل می‌کند.
    """
    link = link.strip()

    if not link:
        raise MalformedVlessError("VLESS link cannot be empty")

    parsed = urlparse(link)

    if parsed.scheme.lower() != "vless":
        raise UnsupportedVlessError(f"Only vless:// links are supported, got scheme '{parsed.scheme or '(none)'}'")

    if not parsed.hostname:
        raise MalformedVlessError("Invalid VLESS link: missing host")

    raw_uuid = unquote(parsed.username or "").strip()

    if not raw_uuid:
        raise MalformedVlessError("Invalid VLESS link: missing UUID")

    try:
        parsed_uuid = uuid.UUID(raw_uuid)
    except ValueError as exc:
        raise MalformedVlessError(f"Invalid UUID in VLESS link: {raw_uuid}") from exc

    try:
        port = parsed.port
    except ValueError as exc:
        raise MalformedVlessError("Invalid port in VLESS link") from exc

    if port is None:
        port = DEFAULT_PORT

    if not 1 <= port <= 65535:
        raise MalformedVlessError(f"Invalid port in VLESS link: {port}")

    query = parse_qs(parsed.query, keep_blank_values=True)

    def get_query_value(key: str, default: str = "") -> str:
        """Return the first query value or a default.

        اولین مقدار query یا مقدار پیش‌فرض را برمی‌گرداند.
        """
        values = query.get(key)

        if not values:
            return default

        # parse_qs already URL-decodes query values.
        # parse_qs خودش مقادیر query را decode می‌کند.
        return values[0]

    def get_bool_query_value(key: str, default: bool = False) -> bool:
        """Return a normalized boolean query value.

        مقدار بولین نرمال‌شده‌ی query را برمی‌گرداند.
        """
        value = get_query_value(key).strip().lower()

        if value in {"1", "true", "yes", "on"}:
            return True

        if value in {"0", "false", "no", "off"}:
            return False

        return default

    security = get_query_value("security").strip().lower()

    if security != REQUIRED_SECURITY:
        raise UnsupportedVlessError(f"only security={REQUIRED_SECURITY} is supported, got '{security or '(none)'}'")

    flow = get_query_value("flow").strip()

    if flow != REQUIRED_FLOW:
        raise UnsupportedVlessError(f"only flow={REQUIRED_FLOW} is supported, got '{flow or '(none)'}'")

    public_key = get_query_value("pbk").strip()

    if not public_key:
        raise MalformedVlessError("vless+reality link is missing the 'pbk' (Reality public key) parameter")

    hostname = parsed.hostname
    sni = get_query_value("sni").strip() or get_query_value("host").strip()

    # URI fragment is the user-visible profile remark.
    # fragment در URI همان remark قابل‌نمایش پروفایل است.
    remark = unquote(parsed.fragment).strip()

    if not remark:
        remark = f"{hostname}:{port}"

    profile_id = uuid.uuid4().hex

    outbound: VlessOutbound = {
        "protocol": "vless",
        "address": hostname,
        "port": port,
        "id": str(parsed_uuid),
        "flow": flow,
        "security": security,
        "sni": sni,
        "fp": get_query_value("fp", DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT,
        "publicKey": public_key,
        "shortId": get_query_value("sid").strip(),
        "spiderX": get_query_value("spx"),
        "encryption": get_query_value(
            "encryption",
            DEFAULT_ENCRYPTION,
        ).strip()
        or DEFAULT_ENCRYPTION,
        "type": get_query_value(
            "type",
            DEFAULT_NETWORK,
        ).strip()
        or DEFAULT_NETWORK,
        "path": get_query_value("path"),
        "host": get_query_value("host"),
        "serviceName": get_query_value("serviceName"),
        "authority": get_query_value("authority"),
        "mode": get_query_value("mode"),
        "alpn": get_query_value("alpn"),
        "headerType": get_query_value("headerType"),
        "seed": get_query_value("seed"),
        "packetEncoding": get_query_value("packetEncoding"),
        "mux": get_query_value("mux"),
        "allowInsecure": get_bool_query_value("allowInsecure"),
        "ech": get_query_value("ech"),
        "echForceQuery": get_query_value("echForceQuery"),
        "pqv": get_query_value("pqv"),
    }

    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark=remark,
        outbound_config=dict(outbound),
        added_at_iso=datetime.now(timezone.utc).isoformat(),
    )
