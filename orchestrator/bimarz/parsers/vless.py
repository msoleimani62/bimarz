"""
VLESS share-link parser.
پارسر لینک اشتراک VLESS.
"""

from __future__ import annotations

import uuid
from typing import TypedDict
from urllib.parse import parse_qs, unquote, urlparse

from bimarz.models import ServerProfile


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
    fragment: str
    mux: str
    allowInsecure: bool
    ech: str
    echForceQuery: str
    pqv: str


def parse_vless_link(link: str) -> ServerProfile:
    """Parse a VLESS share link into a ServerProfile.
    یک لینک اشتراک VLESS را به ServerProfile تبدیل می‌کند.
    """
    link = link.strip()
    if not link.startswith("vless://"):
        raise ValueError("Only vless:// links are supported")

    parsed = urlparse(link)
    if not parsed.hostname:
        raise ValueError("Invalid VLESS link: missing host")

    raw_uuid = unquote(parsed.username or "")
    if not raw_uuid:
        raise ValueError("Invalid VLESS link: missing UUID")

    try:
        uuid.UUID(raw_uuid)
    except ValueError as exc:
        raise ValueError(f"Invalid UUID in VLESS link: {raw_uuid}") from exc

    port = parsed.port or 443
    query = parse_qs(parsed.query)

    def _q(key: str, default: str = "") -> str:
        vals = query.get(key)
        return vals[0] if vals else default

    def _qb(key: str, default: bool = False) -> bool:
        val = _q(key, "").lower()
        if val in ("1", "true", "yes", "on"):
            return True
        if val in ("0", "false", "no", "off"):
            return False
        return default

    name = unquote(parsed.fragment) if parsed.fragment else f"{parsed.hostname}:{port}"
    profile_id = uuid.uuid4().hex

    outbound: VlessOutbound = {
        "protocol": "vless",
        "address": parsed.hostname or "",
        "port": port,
        "id": raw_uuid,
        "flow": _q("flow", "xtls-rprx-vision"),
        "security": _q("security", "reality"),
        "sni": _q("sni", _q("host", "")),
        "fp": _q("fp", "chrome"),
        "publicKey": _q("pbk", ""),
        "shortId": _q("sid", ""),
        "spiderX": _q("spx", ""),
        "encryption": _q("encryption", "none"),
        "type": _q("type", "tcp"),
        "path": _q("path", ""),
        "host": _q("host", ""),
        "serviceName": _q("serviceName", ""),
        "authority": _q("authority", ""),
        "mode": _q("mode", ""),
        "alpn": _q("alpn", ""),
        "headerType": _q("headerType", ""),
        "seed": _q("seed", ""),
        "packetEncoding": _q("packetEncoding", ""),
        "fragment": _q("fragment", ""),
        "mux": _q("mux", ""),
        "allowInsecure": _qb("allowInsecure", False),
        "ech": _q("ech", ""),
        "echForceQuery": _q("echForceQuery", ""),
        "pqv": _q("pqv", ""),
    }

    return ServerProfile(
        profile_id=profile_id,
        name=name,
        outbound=dict(outbound),
    )
