"""Integration tests requiring a real xray-core binary.

These tests require:
- xray-core executable available in PATH
- Rust extension built with maturin develop --release

Tests are skipped automatically when requirements are missing.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

import pytest
from bimarz.engine import EngineNotBuiltError, get_engine_client_class
from bimarz.xray_manager import XrayProcess, find_xray_binary, probe_tcp_port

pytestmark = pytest.mark.integration


GRPC_ENDPOINT = "http://127.0.0.1:10085"
GRPC_HOST = "127.0.0.1"
GRPC_PORT = 10085

GRPC_TIMEOUT_SECONDS = 5.0
MAX_STARTUP_WAIT_SECONDS = 10.0

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "xray"
MINIMAL_CONFIG_PATH = FIXTURE_DIR / "minimal_config.json"


@pytest.fixture(scope="module")
def xray_binary() -> Path | None:
    return find_xray_binary()


@pytest.fixture
def xray_process(xray_binary: Path | None):
    if xray_binary is None:
        pytest.skip("xray-core binary not found in PATH")

    if not MINIMAL_CONFIG_PATH.exists():
        pytest.skip("minimal xray fixture config not found")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "integration.json"

        config_path.write_text(
            MINIMAL_CONFIG_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        process = XrayProcess(
            binary_path=xray_binary,
            config_path=config_path,
        )

        process.start()

        try:
            yield process
        finally:
            process.stop()


@pytest.fixture
def running_xray(xray_process: XrayProcess) -> XrayProcess:
    deadline = time.monotonic() + MAX_STARTUP_WAIT_SECONDS

    while time.monotonic() < deadline:
        if asyncio.run(
            probe_tcp_port(
                GRPC_HOST,
                GRPC_PORT,
                timeout=1.0,
            )
        ):
            return xray_process

        time.sleep(0.5)

    pytest.skip(f"xray gRPC API unavailable on {GRPC_HOST}:{GRPC_PORT}")


def get_client_class() -> type:
    try:
        return get_engine_client_class()
    except EngineNotBuiltError:
        pytest.skip("Rust extension is not built")


async def connect_client():
    return await asyncio.wait_for(
        get_client_class().connect(GRPC_ENDPOINT),
        timeout=GRPC_TIMEOUT_SECONDS,
    )


def test_xray_binary_is_available(
    xray_binary: Path | None,
) -> None:
    if xray_binary is None:
        pytest.skip("xray-core binary not found")

    assert xray_binary.exists()
    assert xray_binary.is_file()


def test_xray_process_starts(
    xray_process: XrayProcess,
) -> None:
    assert xray_process.is_alive()
    assert xray_process.pid is not None


def test_grpc_api_responds(
    running_xray: XrayProcess,
) -> None:
    async def probe() -> None:
        client = await connect_client()

        with pytest.raises(RuntimeError) as exc_info:
            await client.get_outbound_stats("__missing_integration_probe__")

        assert exc_info.value is not None

    asyncio.run(probe())


def test_multiple_grpc_connections(
    running_xray: XrayProcess,
) -> None:
    async def connect_multiple() -> None:
        first = await connect_client()
        second = await connect_client()

        assert first is not None
        assert second is not None

    asyncio.run(connect_multiple())
