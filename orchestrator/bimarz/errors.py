"""Centralized error hints for CLI presentation."""

from __future__ import annotations

from bimarz.engine import EngineNotBuiltError
from bimarz.xray_manager import BinaryNotFoundError

_HINTS = {
    EngineNotBuiltError: 'source .venv/bin/activate && maturin develop --release',
    BinaryNotFoundError: "install xray-core or use --xray-bin /path/to/xray; run 'bimarz doctor' for full diagnostics",
}

def get_hint(exc: Exception) -> str | None:
    for exc_type, hint in _HINTS.items():
        if isinstance(exc, exc_type):
            return hint
    return None
