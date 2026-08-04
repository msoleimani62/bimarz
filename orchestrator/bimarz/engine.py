"""Thin Python wrapper around the compiled Rust extension
(`bimarz._engine_core`).

Isolating the import in one place means the rest of the codebase never
has to know the extension module's exact name/path, and a clean,
understandable error is raised if it has not been built yet (e.g. someone
ran `pip install .` instead of `maturin develop --release`) instead of a
raw ImportError leaking out of some deep call site.

پوشش نازک پایتونی روی ماژول Rust کامپایل‌شده (`bimarz._engine_core`).

جدا نگه‌داشتن import در یک جا یعنی بقیه‌ی کدبیس هرگز لازم نیست اسم/مسیر
دقیق ماژول کامپایل‌شده را بداند، و اگر هنوز ساخته نشده باشد (مثلاً کسی
`pip install .` زده به‌جای `maturin develop --release`) یک خطای واضح و
قابل‌فهم پرتاب می‌شود، نه یک ImportError خام از یک نقطه‌ی عمیق فراخوانی.
"""

from __future__ import annotations

import asyncio
import inspect
from contextlib import suppress


class EngineNotBuiltError(Exception):
    """Raised when the compiled Rust extension cannot be imported.

    زمانی پرتاب می‌شود که ماژول کامپایل‌شده‌ی Rust قابل import نباشد.
    """


def get_engine_client_class():
    """Returns the PyEngineClient class from the compiled Rust extension.

    Imported lazily (inside a function, not at module load time) so that
    commands which never need the engine (like `bimarz profile list`)
    don't fail just because the Rust extension isn't built yet.

    کلاس PyEngineClient را از ماژول کامپایل‌شده‌ی Rust برمی‌گرداند.

    به‌صورت lazy (داخل یک تابع، نه در زمان بارگذاری ماژول) import می‌شود
    تا دستورهایی که هرگز به engine نیاز ندارند (مثل `bimarz profile
    list`) فقط به این دلیل که ماژول Rust ساخته نشده fail نکنند.
    """
    try:
        from bimarz._engine_core import PyEngineClient
    except ImportError as exc:
        raise EngineNotBuiltError(
            "the compiled Rust extension is not available. Build it with "
            "'maturin develop --release' from the project root."
        ) from exc
    return PyEngineClient


def get_health_check_function():
    """Returns check_server_health(address, port, timeout_ms) -> (reachable, latency_ms, error_message).

    تابع check_server_health(address, port, timeout_ms) را برمی‌گرداند که
    (reachable, latency_ms, error_message) می‌دهد.
    """
    try:
        from bimarz._engine_core import check_server_health
    except ImportError as exc:
        raise EngineNotBuiltError(
            "the compiled Rust extension is not available. Build it with "
            "'maturin develop --release' from the project root."
        ) from exc
    return check_server_health


def get_batch_health_check_function():
    """Returns check_servers_health(targets, timeout_ms) -> list of
    (profile_id, reachable, latency_ms, error_message), checked in
    parallel.

    تابع check_servers_health(targets, timeout_ms) را برمی‌گرداند که
    لیستی از (profile_id, reachable, latency_ms, error_message) می‌دهد،
    تست‌شده به‌صورت موازی.
    """
    try:
        from bimarz._engine_core import check_servers_health
    except ImportError as exc:
        raise EngineNotBuiltError(
            "the compiled Rust extension is not available. Build it with "
            "'maturin develop --release' from the project root."
        ) from exc
    return check_servers_health


async def probe_grpc_with_engine(endpoint: str, timeout: float) -> bool:
    """Attempts a real gRPC connection through the compiled Rust extension.
    Returns True if the endpoint responds to a gRPC call (even an error
    response proves the service is alive), False on any failure.

    یک اتصال gRPC واقعی از طریق ماژول کامپایل‌شده‌ی Rust امتحان می‌کند.
    True برمی‌گرداند اگر endpoint به یک فراخوانی gRPC پاسخ بدهد (حتی یک
    پاسخ خطا ثابت می‌کند سرویس زنده است)، False در صورت هر شکست.
    """
    try:
        client_class = get_engine_client_class()
    except EngineNotBuiltError:
        return False

    client = None

    try:
        client = await asyncio.wait_for(client_class.connect(endpoint), timeout=timeout)
        # یک فراخوانی بی‌ضرر که حتی اگر tag وجود نداشته باشد، یک پاسخ
        # gRPC واقعی (NOT_FOUND) برمی‌گرداند — این کافی است تا ثابت کند
        # سرویس gRPC واقعاً پاسخ‌ده است.
        # A harmless call that will return a real gRPC response (NOT_FOUND)
        # even if the tag does not exist — enough to prove the gRPC service
        # is actually responding.
        with suppress(Exception):
            await client.get_outbound_stats("__bimarz_probe_nonexistent__")
        return True
    except Exception:
        return False
    finally:
        if client is not None:
            close = getattr(client, "close", None)
            if callable(close):
                with suppress(Exception):
                    result = close()
                    if inspect.isawaitable(result):
                        await result
