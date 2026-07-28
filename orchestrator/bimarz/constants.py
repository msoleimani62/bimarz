"""Project-wide constants: paths, defaults, and the single source of truth
for the version number.

ثابت‌های سراسری پروژه: مسیرها، مقادیر پیش‌فرض، و منبع واحد شماره نسخه.

NOTE: this must be bumped together with `version` in pyproject.toml, exactly
like the ODL_VERSION / pyproject.toml pairing in the open-downloader-cli
project — the two must never drift apart.

نکته: این مقدار باید همزمان با `version` در pyproject.toml آپدیت شود،
دقیقاً مثل جفت ODL_VERSION / pyproject.toml در پروژه‌ی open-downloader-cli؛
این دو هرگز نباید از هم عقب بمانند.
"""

from pathlib import Path

BIMARZ_VERSION = "0.1.0"

# دایرکتوری تنظیمات کاربر: پروفایل‌های سرور رمزنگاری‌شده، لاگ‌ها، کش وضعیت.
# User config directory: encrypted server profiles, logs, cached state.
CONFIG_DIR = Path.home() / ".config" / "bimarz"
PROFILES_FILE = CONFIG_DIR / "profiles.enc.json"
LOG_DIR = CONFIG_DIR / "logs"
STATE_FILE = CONFIG_DIR / "state.json"

# مسیر پیش‌فرض باینری xray-core؛ کاربر می‌تواند با --xray-bin رونویسی کند.
# Default path to the xray-core binary; user can override with --xray-bin.
DEFAULT_XRAY_BINARY = "xray"

# آدرس پیش‌فرض gRPC محلی که xray-core باید طبق کانفیگ روی آن گوش دهد.
# Default local gRPC address xray-core should listen on per its config.
DEFAULT_GRPC_ENDPOINT = "http://127.0.0.1:10085"

# پورت گوش‌دادن پیش‌فرض SOCKS محلی که xray-core برای ترافیک عبوری کاربر
# فراهم می‌کند.
# Default local SOCKS listen port that xray-core provides for the user's
# outgoing traffic.
DEFAULT_LOCAL_SOCKS_PORT = 1080

# چند بار و با چه فاصله‌ای بعد از اجرای xray-core تلاش شود تا gRPC API
# بالا بیاید، قبل از این‌که خطای اتصال گزارش شود.
# How many times, and how far apart, to retry the gRPC API after starting
# xray-core before reporting a connection error.
GRPC_CONNECT_RETRY_ATTEMPTS = 10
GRPC_CONNECT_RETRY_DELAY_SECONDS = 0.5

# مهلت زمانی پیش‌فرض (ثانیه) برای هر تست سلامت یک سرور.
# Default timeout (seconds) for each per-server health check.
HEALTHCHECK_TIMEOUT_SECONDS = 5.0
