"""Centralized error hints for CLI presentation.

This module maps exception types to user-facing hint strings so that
command modules do not repeat them.
"""

from __future__ import annotations

from bimarz.engine import EngineNotBuiltError
from bimarz.xray_manager import BinaryNotFoundError

_HINTS: dict[type[Exception], str] = {
    EngineNotBuiltError: (
        "source .venv/bin/activate && maturin develop --release"
    ),
    BinaryNotFoundError: (
        "install xray-core or use --xray-bin /path/to/xray; "
        "run 'bimarz doctor' for full diagnostics"
    ),
}


def get_hint(exc: Exception) -> str | None:
    """Return a contextual hint for a known error, or None."""
    for exc_type, hint in _HINTS.items():
        if isinstance(exc, exc_type):
            return hint
    return None
