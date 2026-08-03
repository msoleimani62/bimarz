"""
Small stateless helper functions shared across services and commands.
توابع کمکی کوچک و بدون‌حالت که بین سرویس‌ها و دستورات مشترک هستند.
"""

from __future__ import annotations

import os
from typing import Any

from bimarz.constants import ACTIVE_OUTBOUND_TAG
from bimarz.models import ServerProfile


def get_current_uid() -> int | None:
    """Return current user UID when available.
    شناسه کاربری فعلی را در صورت وجود برمی‌گرداند.
    """
    if hasattr(os, "getuid"):
        return os.getuid()
    return None


def get_outbound(profile: ServerProfile) -> dict[str, Any]:
    """Return the raw outbound dict stored on a profile.
    دیکشنری خام outbound ذخیره‌شده روی پروفایل را برمی‌گرداند.
    """
    return getattr(profile, "outbound", None) or {}


def format_profile_address(profile: ServerProfile) -> str:
    """Return a display-friendly address for a profile.
    آدرس مناسب برای نمایش پروفایل را برمی‌گرداند.
    """
    outbound = get_outbound(profile)
    return str(outbound.get("address", "?"))


def outbound_kwargs(profile: ServerProfile) -> dict[str, Any]:
    """Build the kwargs expected by add_vless_reality_outbound.
    kwargs مورد نیاز add_vless_reality_outbound را می‌سازد.
    """
    outbound = get_outbound(profile)
    return {
        "tag": ACTIVE_OUTBOUND_TAG,
        "address": outbound.get("address", ""),
        "port": int(outbound.get("port", 443)),
        "id": outbound.get("id", ""),
        "flow": outbound.get("flow", "xtls-rprx-vision"),
        "security": outbound.get("security", "reality"),
        "sni": outbound.get("sni", ""),
        "fp": outbound.get("fp", "chrome"),
        "pbk": outbound.get("publicKey", ""),
        "sid": outbound.get("shortId", ""),
        "spx": outbound.get("spiderX", ""),
        "network": outbound.get("type", "tcp"),
        "path": outbound.get("path", ""),
        "serviceName": outbound.get("serviceName", ""),
        "authority": outbound.get("authority", ""),
        "mode": outbound.get("mode", ""),
        "alpn": outbound.get("alpn", ""),
        "packetEncoding": outbound.get("packetEncoding", ""),
        "fragment": outbound.get("fragment", ""),
        "mux": outbound.get("mux", ""),
        "allowInsecure": outbound.get("allowInsecure", False),
        "ech": outbound.get("ech", ""),
    }


def profiles_by_id(profiles: list[ServerProfile]) -> dict[str, ServerProfile]:
    """Index a list of profiles by their profile_id.
    فهرست پروفایل‌ها را بر اساس profile_id ایندکس می‌کند.
    """
    return {p.profile_id: p for p in profiles}
