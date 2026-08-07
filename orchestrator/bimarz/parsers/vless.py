"""
VLESS share-link parser.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    """Parse a VLESS share link into a ServerProfile."""
    link = link.strip()

    if not link:
        raise ValueError("VLESS link cannot be empty")

    parsed = urlparse(link)

    if parsed.scheme != "vless":
        raise ValueError("Only vless:// links are supported")

    if not parsed.hostname:
        raise ValueError("Invalid VLESS link: missing host")

    raw_uuid = unquote(parsed.username or "").strip()

    if not raw_uuid:
        raise ValueError("Invalid VLESS link: missing UUID")

    try:
        parsed_uuid = uuid.UUID(raw_uuid)
    except ValueError as exc:
        raise ValueError(f"Invalid UUID in VLESS link: {raw_uuid}") from exc

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid port in VLESS link") from exc

    if port is None:
        port = 443
    elif not 1 <= port <= 65535:
        raise ValueError(f"Invalid port in VLESS link: {port}")

    query = parse_qs(parsed.query, keep_blank_values=True)

    def get_query_value(key: str, default: str = "") -> str:
        """Return the first query value or a default."""
        values = query.get(key)

        if not values:
            return default

        return unquote(values[0])

    def get_bool_query_value(key: str, default: bool = False) -> bool:
        """Return a normalized boolean query value."""
        value = get_query_value(key).strip().lower()

        if value in {"1", "true", "yes", "on"}:
            return True

        if value in {"0", "false", "no", "off"}:
            return False

        return default

    hostname = parsed.hostname
    sni = get_query_value("sni") or get_query_value("host")

    name = unquote(parsed.fragment).strip()
    if not name:
        name = f"{hostname}:{port}"

    profile_id = uuid.uuid4().hex

    outbound: VlessOutbound = {
        "protocol": "vless",
        "address": hostname,
        "port": port,
        "id": str(parsed_uuid),
        "flow": get_query_value("flow", "xtls-rprx-vision"),
        "security": get_query_value("security", "reality"),
        "sni": sni,
        "fp": get_query_value("fp", "chrome"),
        "publicKey": get_query_value("pbk"),
        "shortId": get_query_value("sid"),
        "spiderX": get_query_value("spx"),
        "encryption": get_query_value("encryption", "none"),
        "type": get_query_value("type", "tcp"),
        "path": get_query_value("path"),
        "host": get_query_value("host"),
        "serviceName": get_query_value("serviceName"),
        "authority": get_query_value("authority"),
        "mode": get_query_value("mode"),
        "alpn": get_query_value("alpn"),
        "headerType": get_query_value("headerType"),
        "seed": get_query_value("seed"),
        "packetEncoding": get_query_value("packetEncoding"),
        "fragment": get_query_value("fragment"),
        "mux": get_query_value("mux"),
        "allowInsecure": get_bool_query_value("allowInsecure"),
        "ech": get_query_value("ech"),
        "echForceQuery": get_query_value("echForceQuery"),
        "pqv": get_query_value("pqv"),
    }

    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark=name,
        outbound_config=dict(outbound),
        added_at_iso=datetime.now(timezone.utc).isoformat(),
    )
