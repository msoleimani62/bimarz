"""
Small stateless helper functions shared across services and commands.
"""

from __future__ import annotations

import os
from typing import Any

from bimarz.constants import ACTIVE_OUTBOUND_TAG
from bimarz.models import ServerProfile


def get_current_uid() -> int | None:
    """Return the current process UID when supported."""
    # Return the current user ID when supported by the operating system.
    getuid = getattr(os, "getuid", None)

    if getuid is None:
        return None

    return getuid()


def get_outbound(profile: ServerProfile) -> dict[str, Any]:
    """Return the raw outbound configuration stored on a profile."""
    # Normalize missing or invalid outbound data to an empty mapping.
    outbound = getattr(profile, "outbound_config", None)

    if not isinstance(outbound, dict):
        return {}

    return outbound


def format_profile_address(profile: ServerProfile) -> str:
    """Return a display-friendly address for a profile."""
    # Provide a stable fallback when the outbound address is unavailable.
    address = get_outbound(profile).get("address")

    return str(address) if address else "?"


def outbound_kwargs(profile: ServerProfile) -> dict[str, Any]:
    """Build arguments expected by add_vless_reality_outbound."""
    # Normalize the values required by the Rust outbound builder.
    outbound = get_outbound(profile)

    raw_port = outbound.get("port", 443)

    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid outbound port: {raw_port!r}") from exc

    if not 1 <= port <= 65535:
        raise ValueError(f"Outbound port out of range: {port}")

    return {
        "tag": ACTIVE_OUTBOUND_TAG,
        "uuid": str(outbound.get("id", "")),
        "flow": str(outbound.get("flow", "xtls-rprx-vision")),
        "address": str(outbound.get("address", "")),
        "port": port,
        "network": str(outbound.get("type", "tcp")),
        "sni": str(outbound.get("sni", "")),
        "fingerprint": str(outbound.get("fp", "chrome")),
        "public_key_b64": str(outbound.get("publicKey", "")),
        "short_id_hex": str(outbound.get("shortId", "")),
        "spider_x": str(outbound.get("spiderX", "")),
    }


def profiles_by_id(profiles: list[ServerProfile]) -> dict[str, ServerProfile]:
    """Index profiles by profile_id."""
    # Build a direct lookup table for efficient profile retrieval.
    return {profile.profile_id: profile for profile in profiles}
