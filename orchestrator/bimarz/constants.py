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

BIMARZ_VERSION = "0.2.0"

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

# چند بار متوالی باید تست سلامت پروفایل فعال fail شود تا failover
# خودکار فعال شود.
# How many consecutive failed health checks on the active profile before
# automatic failover kicks in.
FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD = 3

# فاصله‌ی زمانی (ثانیه) بین دورهای تست سلامت در طول یک اتصال با
# --auto-failover فعال.
# Interval (seconds) between health-check rounds during a connection with
# --auto-failover enabled.
FAILOVER_CHECK_INTERVAL_SECONDS = 30.0

# مهلت زمانی پیش‌فرض (ثانیه) برای probe پورت gRPC در doctor.
# Default timeout (seconds) for the gRPC port probe in doctor.
DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS = 2.0

# نام متغیر محیطی برای override کردن timeout مربوط به doctor.
# Environment variable name to override the doctor probe timeout.
DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR = "BIMARZ_DOCTOR_TIMEOUT"

# Tag for the active xray outbound managed by bimarz.
# تگ outbound فعال که توسط bimarز مدیریت می‌شود.
ACTIVE_OUTBOUND_TAG = "bimarz-active"

# Default gRPC host for local xray-core API.
# میزبان پیش‌فرض gRPC برای API محلی xray-core.
DEFAULT_GRPC_HOST = "127.0.0.1"

# Default gRPC port for local xray-core API.
# پورت پیش‌فرض gRPC برای API محلی xray-core.
DEFAULT_GRPC_PORT = 10085

# Maximum retries when connecting to the engine.
# حداکثر تلاش مجدد هنگام اتصال به engine.
ENGINE_CONNECT_MAX_RETRIES = 5

# Delay between engine connection retries in seconds.
# فاصله زمانی بین تلاش‌های مجدد اتصال engine بر حسب ثانیه.
ENGINE_CONNECT_RETRY_DELAY = 1.0
