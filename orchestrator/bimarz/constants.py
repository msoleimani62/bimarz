"""
Project-wide constants.

ثابت‌های سراسری پروژه.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path


def _resolve_bimarz_version() -> str:
    """Resolve the project version from the installed package metadata.

    `pyproject.toml` is the single source of truth for the BiMarz version;
    the constant below is only a fallback for running from a bare source
    tree where the package was never installed.

    نسخه‌ی پروژه از metadata پکیج نصب‌شده خوانده می‌شود. `pyproject.toml`
    تنها مرجع معتبر نسخه‌ی BiMarz است؛ مقدار ثابت پایین فقط fallback برای
    اجرا از درخت سورس خام است که پکیج در آن نصب نشده.
    """
    try:
        return _package_version("bimarz")
    except PackageNotFoundError:
        return "0.2.2"  # fallback: keep in sync with pyproject.toml


BIMARZ_VERSION = _resolve_bimarz_version()

# دایرکتوری تنظیمات کاربر: پروفایل‌های سرور رمزنگاری‌شده، لاگ‌ها و کش وضعیت.
# User config directory: encrypted server profiles, logs, and cached state.
CONFIG_DIR = Path.home() / ".config" / "bimarz"
PROFILES_FILE = CONFIG_DIR / "profiles.enc.json"
LOG_DIR = CONFIG_DIR / "logs"
STATE_FILE = CONFIG_DIR / "state.json"

# مسیر پیش‌فرض باینری xray-core.
# Default path to the xray-core binary.
DEFAULT_XRAY_BINARY = "xray"

# آدرس پیش‌فرض gRPC محلی xray-core.
# Default local xray-core gRPC endpoint.
DEFAULT_GRPC_ENDPOINT = "http://127.0.0.1:10085"

# پورت پیش‌فرض SOCKS محلی.
# Default local SOCKS port.
DEFAULT_LOCAL_SOCKS_PORT = 1080

# تعداد و فاصله تلاش‌های اتصال gRPC.
# Number and delay of gRPC connection retries.
GRPC_CONNECT_RETRY_ATTEMPTS = 10
GRPC_CONNECT_RETRY_DELAY_SECONDS = 0.5

# مهلت پیش‌فرض health check.
# Default health-check timeout.
HEALTHCHECK_TIMEOUT_SECONDS = 5.0

# تعداد شکست متوالی لازم برای failover.
# Consecutive failures required before failover.
FAILOVER_CONSECUTIVE_FAILURES_THRESHOLD = 3

# فاصله بین health checkها در failover.
# Interval between failover health-check rounds.
FAILOVER_CHECK_INTERVAL_SECONDS = 30.0

# مهلت probe پورت gRPC در doctor.
# Default gRPC doctor probe timeout.
DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS = 2.0

# نام متغیر محیطی timeout مربوط به doctor.
# Environment variable overriding the doctor timeout.
DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR = "BIMARZ_DOCTOR_TIMEOUT"

# تگ canonical برای outbound فعال.
# Canonical tag for the active managed outbound.
ACTIVE_OUTBOUND_TAG = "bimarz-active"

# میزبان پیش‌فرض API محلی gRPC.
# Default local gRPC API host.
DEFAULT_GRPC_HOST = "127.0.0.1"

# پورت پیش‌فرض API محلی gRPC.
# Default local gRPC API port.
DEFAULT_GRPC_PORT = 10085

# حداکثر تلاش اتصال engine.
# Maximum engine connection retries.
ENGINE_CONNECT_MAX_RETRIES = 5

# فاصله تلاش‌های اتصال engine.
# Delay between engine connection retries.
ENGINE_CONNECT_RETRY_DELAY = 1.0
