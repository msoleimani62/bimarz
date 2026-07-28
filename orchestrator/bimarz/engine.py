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
