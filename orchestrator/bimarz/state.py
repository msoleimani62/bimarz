"""Shared globals: the rich Console instance and the debug flag.

Kept in its own module (same as open-downloader-cli's state.py) purely to
avoid circular imports between cli.py and the modules it calls.

متغیرهای سراسری مشترک: نمونه‌ی کنسول rich و پرچم دیباگ.

در ماژول جداگانه‌ی خودش نگه داشته شده (دقیقاً مثل state.py در
open-downloader-cli) فقط برای جلوگیری از import حلقوی بین cli.py و
ماژول‌هایی که صدا می‌زند.
"""

from rich.console import Console

console = Console()
DEBUG = False
