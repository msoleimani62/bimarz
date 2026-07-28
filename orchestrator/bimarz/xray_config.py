"""Generates the xray-core JSON config used by `bimarz connect`.

Builds the same shape of config verified manually during phase 2's
end-to-end test: a gRPC API listener (HandlerService+StatsService) plus a
local SOCKS inbound for the user's actual traffic. The real outbound (the
chosen profile) is NOT baked into this file — it is added afterwards via
the gRPC AddOutbound call, so xray-core starts with a placeholder
`freedom` outbound and the real one is added live.

مولد کانفیگ JSON برای xray-core که در `bimarz connect` استفاده می‌شود.

همان شکل کانفیگی را می‌سازد که در تست end-to-end دستی فاز ۲ تایید شد: یک
گوش‌دهنده‌ی gRPC API (به‌همراه HandlerService+StatsService) به‌علاوه یک
inbound محلی از نوع SOCKS برای ترافیک واقعی کاربر. outbound واقعی (پروفایل
انتخاب‌شده) در این فایل جاسازی نمی‌شود — بعداً از طریق فراخوان gRPC
AddOutbound اضافه می‌شود، پس xray-core با یک outbound جای‌نگهدار از نوع
`freedom` شروع می‌شود و outbound واقعی به‌صورت زنده اضافه می‌شود.
"""

from __future__ import annotations

import json

from bimarz.constants import DEFAULT_GRPC_ENDPOINT, DEFAULT_LOCAL_SOCKS_PORT


def _grpc_listen_address(grpc_endpoint: str) -> str:
    """Extracts the "host:port" part xray-core's api.listen field wants
    from a full "http://host:port" endpoint URL.

    بخش "host:port" ای که فیلد api.listen در xray-core می‌خواهد را از یک
    URL کامل "http://host:port" استخراج می‌کند.
    """
    return grpc_endpoint.removeprefix("http://").removeprefix("https://")


def build_connect_config(
    grpc_endpoint: str = DEFAULT_GRPC_ENDPOINT,
    local_socks_port: int = DEFAULT_LOCAL_SOCKS_PORT,
) -> str:
    """Builds the xray-core config JSON as a string, ready to write to a
    file and pass to `xray run -config`.

    کانفیگ JSON مربوط به xray-core را به‌صورت رشته می‌سازد، آماده برای
    نوشتن در یک فایل و پاس دادن به `xray run -config`.
    """
    config = {
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
        # یک outbound جای‌نگهدار تا xray-core بدون خطا بالا بیاید؛ outbound
        # واقعی بعداً زنده از طریق gRPC اضافه می‌شود.
        # A placeholder outbound so xray-core starts without error; the
        # real outbound is added live via gRPC afterwards.
        "outbounds": [{"protocol": "freedom", "tag": "placeholder"}],
    }
    return json.dumps(config, indent=2)
