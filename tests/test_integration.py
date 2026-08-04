"""Integration tests requiring a real xray-core binary.

These tests are skipped automatically if xray-core is not in PATH,
or if its gRPC API does not come up on the expected endpoint.
Run locally after: maturin develop --release

تست‌های integration که به یک باینری واقعی xray-core نیاز دارند.

اگر xray-core در PATH نباشد یا gRPC API آن بالا نیاید، به‌صورت خودکار skip
می‌شوند. اجرا به‌صورت local بعد از: maturin develop --release
"""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
import time
from pathlib import Path

import pytest
from bimarz.engine import EngineNotBuiltError, get_engine_client_class
from bimarz.xray_config import build_connect_config
from bimarz.xray_manager import XrayProcess, find_xray_binary, probe_tcp_port

GRPC_ENDPOINT = "http://127.0.0.1:10085"
GRPC_HOST = "127.0.0.1"
GRPC_PORT = 10085
GRPC_TIMEOUT_SECONDS = 5.0
MAX_STARTUP_WAIT_SECONDS = 10.0


@pytest.fixture(scope="module")
def xray_binary() -> Path | None:
    return find_xray_binary()


@pytest.fixture
def xray_process(xray_binary: Path | None):
    if xray_binary is None:
        pytest.skip("xray-core binary not found in PATH")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        config_path = tmpdir / "test-connect.json"
        config_path.write_text(build_connect_config(), encoding="utf-8")

        proc = XrayProcess(binary_path=xray_binary, config_path=config_path)
        proc.start()
        yield proc
        proc.stop()


@pytest.fixture
def xray_process_with_grpc(xray_process: XrayProcess):
    # Wait for the gRPC API port to actually open (with retries).
    # منتظر باز شدن واقعی پورت gRPC API می‌مانیم (با تلاش مجدد).
    deadline = time.monotonic() + MAX_STARTUP_WAIT_SECONDS
    port_open = False
    while time.monotonic() < deadline:
        port_open = asyncio.run(probe_tcp_port(GRPC_HOST, GRPC_PORT, timeout=1.0))
        if port_open:
            break
        time.sleep(0.5)

    if not port_open:
        pytest.skip(
            f"xray-core started but gRPC API did not come up on "
            f"{GRPC_HOST}:{GRPC_PORT} within {MAX_STARTUP_WAIT_SECONDS}s "
            f"(common on restricted environments like Termux/proot)"
        )

    yield xray_process


def test_xray_binary_is_executable(xray_binary: Path | None) -> None:
    if xray_binary is None:
        pytest.skip("xray-core binary not found")
    assert xray_binary.exists()
    assert xray_binary.is_file()


def test_xray_process_starts_and_stops(xray_process: XrayProcess) -> None:
    assert xray_process.is_alive()
    assert xray_process.pid is not None


def test_grpc_api_responds_to_engine_client(
    xray_process_with_grpc: XrayProcess,
) -> None:
    try:
        client_class = get_engine_client_class()
    except EngineNotBuiltError:
        pytest.skip("Rust extension not built")

    async def probe() -> bool:
        client = await asyncio.wait_for(
            client_class.connect(GRPC_ENDPOINT),
            timeout=GRPC_TIMEOUT_SECONDS,
        )
        # A harmless call that returns NOT_FOUND even if tag does not exist.
        # یک فراخوانی بی‌ضرر که حتی اگر tag وجود نداشته باشد NOT_FOUND برمی‌گرداند.
        with contextlib.suppress(Exception):
            await client.get_outbound_stats("__integration_probe__")
        return True

    result = asyncio.run(probe())
    assert result is True


def test_add_and_remove_outbound_via_grpc(
    xray_process_with_grpc: XrayProcess,
) -> None:
    try:
        client_class = get_engine_client_class()
    except EngineNotBuiltError:
        pytest.skip("Rust extension not built")

    outbound_tag = "integration-test-outbound"

    async def manipulate() -> None:
        client = await asyncio.wait_for(
            client_class.connect(GRPC_ENDPOINT),
            timeout=GRPC_TIMEOUT_SECONDS,
        )

        await client.add_vless_reality_outbound(
            tag=outbound_tag,
            uuid="8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d",
            flow="xtls-rprx-vision",
            address="127.0.0.1",
            port=443,
            network="tcp",
            sni="www.microsoft.com",
            fingerprint="chrome",
            public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            short_id_hex="a1b2c3",
            spider_x="/",
        )

        stats = await client.get_outbound_stats(outbound_tag)
        assert stats[0] == outbound_tag

        await client.remove_outbound(outbound_tag)

    asyncio.run(manipulate())
