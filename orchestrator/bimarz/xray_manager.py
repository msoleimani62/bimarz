"""Manages the xray-core binary as a subprocess: locating it, starting it,
stopping it, and reading its version.

Follows the same architectural rule already proven in
open-downloader-cli's cookies.py/proxy_pool.py: this module never calls
sys.exit(); every failure is a raised exception, and the caller (cli.py)
decides how to present it to the user.

مدیریت باینری xray-core به‌عنوان یک subprocess: پیدا کردن، اجرا، توقف، و
خواندن نسخه‌اش.

از همان قانون معماری‌ای که در cookies.py/proxy_pool.py پروژه‌ی
open-downloader-cli اثبات شده پیروی می‌کند: این ماژول هرگز sys.exit()
صدا نمی‌زند؛ هر خطا یک استثنای پرتاب‌شده است، و فراخوان (cli.py) تصمیم
می‌گیرد چطور آن را به کاربر نشان دهد.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import threading
from pathlib import Path


class XrayManagerError(Exception):
    """Base class for all xray_manager errors.

    کلاس پایه برای تمام خطاهای xray_manager.
    """


class BinaryNotFoundError(XrayManagerError):
    """Raised when the xray-core binary cannot be located anywhere.

    زمانی پرتاب می‌شود که باینری xray-core در هیچ‌کجا پیدا نشود.
    """


class ProcessStartError(XrayManagerError):
    """Raised when the xray-core process fails to start.

    زمانی پرتاب می‌شود که پروسه‌ی xray-core نتواند اجرا شود.
    """


class ProcessAlreadyRunningError(XrayManagerError):
    """Raised when trying to start a process that is already running.

    زمانی پرتاب می‌شود که تلاش شود پروسه‌ای که از قبل در حال اجراست دوباره
    اجرا شود.
    """


def find_xray_binary(explicit_path: str | None = None) -> Path | None:
    """Locate the xray-core binary. Prefers an explicit path (e.g. from
    --xray-bin) and falls back to searching $PATH.

    باینری xray-core را پیدا می‌کند. مسیر صریح (مثلاً از --xray-bin) را
    ترجیح می‌دهد و در غیر این صورت در $PATH جستجو می‌کند.
    """
    if explicit_path:
        candidate = Path(explicit_path)
        return (
            candidate
            if candidate.is_file() and os.access(candidate, os.X_OK)
            else None
        )

    found = shutil.which("xray")
    return Path(found) if found else None


def get_xray_version(binary_path: Path, timeout_seconds: float = 5.0) -> str:
    """Runs `xray version` and returns its first output line.

    دستور `xray version` را اجرا می‌کند و اولین خط خروجی‌اش را برمی‌گرداند.
    """
    try:
        completed = subprocess.run(
            [str(binary_path), "version"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise XrayManagerError(f"failed to run '{binary_path} version': {exc}") from exc

    first_line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    if not first_line:
        raise XrayManagerError(f"'{binary_path} version' produced no output")
    return first_line


async def probe_tcp_port(host: str, port: int, timeout: float) -> bool:
    """Attempts a raw TCP connection to host:port. Returns True if the
    port is open, False otherwise. Never raises.

    یک اتصال TCP خام به host:port امتحان می‌کند. True برمی‌گرداند اگر پورت
    باز باشد، در غیر این صورت False. هرگز استثنا پرتاب نمی‌کند.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


class XrayProcess:
    """A thin, testable wrapper around a running xray-core subprocess.

    Deliberately holds no global state — the caller owns the instance and
    its lifetime, which keeps this class easy to unit-test with a fake
    subprocess.Popen.

    یک پوشش نازک و قابل‌تست دور یک subprocess در حال اجرای xray-core.

    عمداً هیچ حالت سراسری نگه نمی‌دارد — فراخوان مالک نمونه و طول عمرش
    است، که این کلاس را با یک subprocess.Popen جعلی به‌راحتی قابل‌تست
    نگه می‌دارد.
    """

    def __init__(self, binary_path: Path, config_path: Path) -> None:
        self._binary_path = binary_path
        self._config_path = config_path
        self._proc: subprocess.Popen | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

    @staticmethod
    def _drain_stream(stream) -> None:
        """Continuously read and discard stream content to prevent pipe deadlock.

        محتوای stream را به‌طور مداوم می‌خواند و دور می‌ریزد تا از deadlock
        ناشی از پر شدن pipe جلوگیری کند.
        """
        if stream is None:
            return
        try:
            for _ in stream:
                pass
        except (ValueError, OSError):
            # Stream already closed or process terminated.
            # استریم قبلاً بسته شده یا پروسه خاتمه یافته.
            pass

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            raise ProcessAlreadyRunningError(
                f"xray-core is already running with PID {self._proc.pid}"
            )

        try:
            self._proc = subprocess.Popen(
                [str(self._binary_path), "run", "-config", str(self._config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise ProcessStartError(f"could not start xray-core: {exc}") from exc

        # Drain pipes in background threads to avoid deadlock when buffers fill.
        # pipeها را در threadهای پس‌زمینه خالی می‌کنیم تا از deadlock جلوگیری شود.
        self._stdout_thread = threading.Thread(
            target=self._drain_stream,
            args=(self._proc.stdout,),
            daemon=True,
            name="xray-stdout-drain",
        )
        self._stderr_thread = threading.Thread(
            target=self._drain_stream,
            args=(self._proc.stderr,),
            daemon=True,
            name="xray-stderr-drain",
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        if self._proc is None:
            return

        self._proc.terminate()
        try:
            self._proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            # اگر با پایان مهربانانه (terminate) در مهلت زمانی جواب نداد،
            # به‌صورت اجباری kill می‌کنیم.
            # If it did not respond to the graceful terminate within the
            # timeout, force-kill it.
            self._proc.kill()
            self._proc.wait(timeout=timeout_seconds)
        finally:
            # Close streams so drain threads can exit cleanly.
            # استریم‌ها را می‌بندیم تا threadهای drain تمیز خارج شوند.
            if self._proc.stdout:
                self._proc.stdout.close()
            if self._proc.stderr:
                self._proc.stderr.close()
            self._proc = None
            self._stdout_thread = None
            self._stderr_thread = None

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None
