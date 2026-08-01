"""DNS leak protection layer: applies DoH config to xray-core runtime config.

لایه‌ی محافظت در برابر نشت DNS: اعمال کانفیگ DoH به کانفیگ runtime xray-core.
"""

from __future__ import annotations

import json

from bimarz.engine import EngineNotBuiltError


def get_default_dns_guard_config() -> dict:
    """Returns the default DNS guard configuration as a Python dict."""
    try:
        from bimarz._engine_core import build_dns_guard_config_json
        return json.loads(build_dns_guard_config_json())
    except EngineNotBuiltError:
        return {
            "servers": ["https+local://1.1.1.1/dns-query"],
            "queryStrategy": "UseIP",
            "tag": "dns-out",
        }


def get_dns_routing_rule() -> dict:
    """Returns a routing rule dict that forces port-53 traffic to the DNS outbound."""
    try:
        from bimarz._engine_core import build_dns_routing_rule_json
        return json.loads(build_dns_routing_rule_json())
    except EngineNotBuiltError:
        return {
            "type": "field",
            "port": "53",
            "network": "udp,tcp",
            "outboundTag": "dns-out",
        }
