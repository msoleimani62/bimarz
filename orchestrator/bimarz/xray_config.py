"""Generates the xray-core JSON config used by `bimarz connect`.

مولد کانفیگ JSON برای xray-core که در `bimarz connect` استفاده می‌شود.
"""

from __future__ import annotations

import json

from bimarz.constants import (
    ACTIVE_OUTBOUND_TAG,
    DEFAULT_GRPC_ENDPOINT,
    DEFAULT_LOCAL_SOCKS_PORT,
)
from bimarz.dns_leak_guard import get_default_dns_guard_config, get_dns_routing_rule

__all__ = [
    "ACTIVE_OUTBOUND_TAG",
    "build_connect_config",
]


def _grpc_listen_address(grpc_endpoint: str) -> str:
    """Extract the host:port part required by xray-core api.listen.

    بخش host:port موردنیاز فیلد api.listen در xray-core را استخراج می‌کند.
    """
    endpoint = grpc_endpoint.strip()
    if not endpoint:
        raise ValueError("grpc_endpoint must not be empty")

    return endpoint.removeprefix("http://").removeprefix("https://")


def build_connect_config(
    grpc_endpoint: str = DEFAULT_GRPC_ENDPOINT,
    local_socks_port: int = DEFAULT_LOCAL_SOCKS_PORT,
    enable_dns_guard: bool = True,
) -> str:
    """Build the xray-core config JSON as a string.

    کانفیگ JSON مربوط به xray-core را به‌صورت رشته می‌سازد.
    """
    if not 1 <= local_socks_port <= 65535:
        raise ValueError("local_socks_port must be between 1 and 65535")

    config: dict = {
        "log": {"loglevel": "warning"},
        "api": {
            "tag": "api",
            "listen": _grpc_listen_address(grpc_endpoint),
            "services": ["HandlerService", "StatsService"],
        },
        "stats": {},
        "policy": {
            "system": {
                "statsInboundUplink": True,
                "statsInboundDownlink": True,
                "statsOutboundUplink": True,
                "statsOutboundDownlink": True,
            }
        },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": local_socks_port,
                "protocol": "socks",
                "settings": {"auth": "noauth"},
                "tag": "socks-in",
            }
        ],
    }

    outbounds = [{"protocol": "freedom", "tag": "placeholder"}]

    if enable_dns_guard:
        outbounds.append({"protocol": "dns", "tag": "dns-out"})
        config["dns"] = get_default_dns_guard_config()

    config["outbounds"] = outbounds

    rules = []

    if enable_dns_guard:
        rules.append(get_dns_routing_rule())

    rules.append(
        {
            "type": "field",
            "inboundTag": ["socks-in"],
            "outboundTag": ACTIVE_OUTBOUND_TAG,
        }
    )

    config["routing"] = {"rules": rules}

    return json.dumps(config, indent=2)
