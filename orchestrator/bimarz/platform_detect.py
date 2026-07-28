"""Runtime environment detection.

Reuses the detection strategy already empirically validated in
open-downloader-cli: a plain env-var check is not reliable inside a Kali
NetHunter chroot (host Android markers are not visible from inside the
chroot), so Android-kernel-specific mount entries in /proc/mounts are
cross-checked against /etc/os-release instead.

تشخیص محیط اجرا.

از همان راهبرد تشخیصی که قبلاً در open-downloader-cli به‌صورت عملی تایید
شده استفاده می‌کند: یک بررسی ساده‌ی متغیر محیطی داخل یک chroot کالی
NetHunter قابل اعتماد نیست (نشانه‌های هاست اندروید از داخل chroot دیده
نمی‌شوند)، پس به‌جایش ورودی‌های mount مخصوص کرنل اندروید در /proc/mounts
با /etc/os-release مقایسه‌متقابل می‌شوند.
"""

from __future__ import annotations

import os
from pathlib import Path

from bimarz.models import Environment

# نشانه‌های mount مخصوص کرنل اندروید که فقط روی یک دستگاه اندرویدی واقعی
# دیده می‌شوند، صرف‌نظر از این‌که داخل proot/chroot باشیم یا نه.
# Android-kernel-specific mount signals only present on a real Android
# device, regardless of whether we are inside a proot/chroot.
_ANDROID_KERNEL_MOUNT_SIGNALS = ("binder", "cpuset", "schedtune", "seclabel")

_PROC_MOUNTS = Path("/proc/mounts")
_OS_RELEASE = Path("/etc/os-release")
_PROC_VERSION = Path("/proc/version")

# فرار اضطراری دستی، برای زمانی که تشخیص خودکار در یک محیط غیرمعمول اشتباه
# حدس بزند.
# Manual escape hatch for when auto-detection guesses wrong in an unusual
# environment.
_FORCE_ENV_VAR = "XO_FORCE_ENVIRONMENT"


def _read_text_safe(path: Path) -> str:
    """Read a file's text content, returning "" on any failure instead of
    raising — detection must never crash the caller.

    محتوای متنی یک فایل را می‌خواند و در صورت هر خطایی "" برمی‌گرداند نه
    این‌که استثنا پرتاب کند — تشخیص هرگز نباید فراخوان را کرش کند.
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_android_kernel_signals() -> bool:
    mounts = _read_text_safe(_PROC_MOUNTS)
    if not mounts:
        return False
    return any(signal in mounts for signal in _ANDROID_KERNEL_MOUNT_SIGNALS)


def _os_release_id() -> str:
    content = _read_text_safe(_OS_RELEASE)
    for line in content.splitlines():
        if line.startswith("ID="):
            return line.split("=", 1)[1].strip().strip('"').lower()
    return ""


def _is_wsl() -> bool:
    version_info = _read_text_safe(_PROC_VERSION).lower()
    return "microsoft" in version_info or "wsl" in version_info


def detect_environment() -> Environment:
    """Detect which of the project's supported environments we are running
    in. Order matters: WSL and the Android-kernel check are both cheap and
    checked before falling back to a plain Linux desktop assumption.

    تشخیص می‌دهد کدام‌یک از محیط‌های پشتیبانی‌شده‌ی پروژه در حال اجراست.
    ترتیب مهم است: بررسی WSL و کرنل اندروید هر دو ارزان هستند و قبل از فرض
    پیش‌فرض دسکتاپ لینوکس بررسی می‌شوند.
    """
    forced = os.environ.get(_FORCE_ENV_VAR)
    if forced:
        try:
            return Environment(forced)
        except ValueError:
            # مقدار نامعتبر force را نادیده می‌گیریم و به تشخیص خودکار
            # برمی‌گردیم به‌جای کرش کردن.
            # Ignore an invalid force value and fall back to auto-detection
            # instead of crashing.
            pass

    if _is_wsl():
        return Environment.WSL

    if _has_android_kernel_signals():
        os_id = _os_release_id()
        if os_id == "kali":
            return Environment.KALI_NETHUNTER
        return Environment.ANDROID_TERMUX

    return Environment.DESKTOP_LINUX
