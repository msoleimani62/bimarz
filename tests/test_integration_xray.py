"""
End-to-end integration tests for the complete BiMarz xray lifecycle.

These tests validate the boundary between:
Python -> Rust extension -> gRPC -> xray-core

تست‌های یکپارچگی انتها به انتها برای چرخه کامل BiMarز.
این تست‌ها مرز بین پایتون، افزونه Rust، gRPC و xray-core را اعتبارسنجی می‌کنند.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import time
from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from bimarz.engine import (
    EngineNotBuiltError,
    get_engine_client_class,
    probe_grpc_with_engine,
)
from bimarz.utils.retry import connect_with_retry
from bimarz.xray_config import build_connect_config
from bimarz.xray_manager import (
    XrayProcess,
    find_xray_binary,
)

# Test constants
# ثابت‌های مورد استفاده در تست‌ها
TEST_XRAY_HOST = "127.0.0.1"
TEST_XRAY_API_PORT = 10085
TEST_OUTBOUND_TAG = "bimarz-integration-test-outbound"
TEST_UUID = "11111111-1111-4111-8111-111111111111"


def _skip_if_xray_missing() -> Path:
    """Skip integration test when xray-core is unavailable.

    اگر xray-core موجود نباشد تست یکپارچگی متوقف می‌شود.
    """
    binary = find_xray_binary()

    if binary is None:
        pytest.skip("xray-core binary not found in PATH; install xray-core before running integration tests")

    return Path(binary)


def _skip_if_engine_missing() -> None:
    """Skip integration test when Rust extension is unavailable.

    اگر افزونه Rust ساخته نشده باشد تست رد می‌شود.
    """
    try:
        get_engine_client_class()
    except EngineNotBuiltError:
        pytest.skip("Rust extension is not built; run maturin develop --release first")


async def _wait_for_tcp_port(
    host: str,
    port: int,
    timeout: float = 5.0,
) -> bool:
    """Wait until a TCP port accepts connections.

    منتظر می‌ماند تا پورت TCP آماده دریافت اتصال شود.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return True
        except OSError:  # noqa: PERF203
            # Retry intentionally while waiting for the TCP service.
            # عمداً تا آماده‌شدن سرویس TCP اتصال را دوباره امتحان می‌کنیم.
            await asyncio.sleep(0.1)

    return False


@pytest.fixture(scope="module")
def xray_binary() -> Path:
    """Resolve xray-core binary once per test module.

    مسیر باینری xray-core را برای کل ماژول تست پیدا می‌کند.
    """
    return _skip_if_xray_missing()


@pytest.fixture
def xray_process(xray_binary: Path) -> Generator[XrayProcess, None, None]:
    """Start and cleanup a real xray-core process.

    یک پردازش واقعی xray-core را اجرا و پاک‌سازی می‌کند.
    """
    with TemporaryDirectory(prefix="bimarz-xray-test-") as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_path.write_text(build_connect_config(), encoding="utf-8")

        process = XrayProcess(
            binary_path=xray_binary,
            config_path=config_path,
        )
        process.start()

        try:
            ready = asyncio.run(
                _wait_for_tcp_port(
                    TEST_XRAY_HOST,
                    TEST_XRAY_API_PORT,
                    timeout=5.0,
                )
            )
            if not ready:
                pytest.fail("xray-core API port did not become available")

            yield process
        finally:
            process.stop()


@pytest.mark.integration
class TestXrayLifecycle:
    """Validate the complete xray-core lifecycle.

    چرخه کامل زندگی xray-core را بررسی می‌کند.
    """

    def test_xray_binary_available(self, xray_binary: Path) -> None:
        """Ensure xray-core executable exists.

        وجود فایل اجرایی xray-core را بررسی می‌کند.
        """
        assert xray_binary.exists()
        assert xray_binary.is_file()

    def test_xray_api_port_available(self, xray_process: XrayProcess) -> None:
        """Ensure xray-core API port accepts connections.

        بررسی می‌کند پورت API xray آماده اتصال است.
        """
        result = asyncio.run(_wait_for_tcp_port(TEST_XRAY_HOST, TEST_XRAY_API_PORT))
        assert result is True

    @pytest.mark.asyncio
    async def test_grpc_probe_responds(self, xray_process: XrayProcess) -> None:
        """Verify Rust gRPC client can communicate with xray-core.

        ارتباط کلاینت Rust از طریق gRPC با xray-core را بررسی می‌کند.
        """
        _skip_if_engine_missing()

        result = await probe_grpc_with_engine(
            f"http://{TEST_XRAY_HOST}:{TEST_XRAY_API_PORT}",
            timeout=5.0,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_add_get_stats_remove_outbound(
        self,
        xray_process: XrayProcess,
    ) -> None:
        """Verify outbound lifecycle through gRPC API.

        چرخه اضافه کردن، خواندن آمار و حذف outbound را بررسی می‌کند.
        """
        _skip_if_engine_missing()

        client_class = get_engine_client_class()
        client = await connect_with_retry(
            client_class,
            endpoint=f"http://{TEST_XRAY_HOST}:{TEST_XRAY_API_PORT}",
            max_retries=10,
            delay=0.5,
        )

        try:
            await client.add_vless_reality_outbound(
                tag=TEST_OUTBOUND_TAG,
                uuid=TEST_UUID,
                flow="xtls-rprx-vision",
                address="127.0.0.1",
                port=1,
                network="tcp",
                sni="localhost",
                fingerprint="chrome",
                public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                short_id_hex="",
                spider_x="/",
            )

            tag, uplink, downlink = await client.get_outbound_stats(TEST_OUTBOUND_TAG)

            assert tag == TEST_OUTBOUND_TAG
            assert isinstance(uplink, int)
            assert isinstance(downlink, int)
            assert uplink >= 0
            assert downlink >= 0

            await client.remove_outbound(TEST_OUTBOUND_TAG)

        finally:
            # Cleanup after partial failures
            # پاک‌سازی بعد از خطاهای احتمالی
            with contextlib.suppress(Exception):
                await client.remove_outbound(TEST_OUTBOUND_TAG)

            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result


@pytest.mark.integration
class TestXrayFailureHandling:
    """Validate integration failure scenarios.

    سناریوهای شکست در یکپارچگی را بررسی می‌کند.
    """

    @pytest.mark.asyncio
    async def test_grpc_connection_failure(self) -> None:
        """Ensure unavailable xray endpoint fails cleanly.

        اطمینان از شکست صحیح اتصال به xray خاموش.
        """
        _skip_if_engine_missing()

        client_class = get_engine_client_class()

        with pytest.raises((ConnectionError, TimeoutError, OSError)):
            await connect_with_retry(
                client_class,
                endpoint="http://127.0.0.1:65530",
                max_retries=2,
                delay=0.1,
            )


@pytest.mark.integration
class TestXrayConfigurationSafety:
    """Validate generated test configuration.

    ایمنی تنظیمات تولیدشده برای تست را بررسی می‌کند.
    """

    def test_generated_config_contains_api_port(self) -> None:
        """Ensure generated xray config exposes API service.

        وجود سرویس API در تنظیمات xray را بررسی می‌کند.
        """
        config = build_connect_config()

        assert isinstance(config, str)
        assert config.strip()
        assert str(TEST_XRAY_API_PORT) in config


@pytest.mark.integration
class TestXrayProcessState:
    """Validate xray process lifecycle state transitions.

    تغییر وضعیت چرخه زندگی پردازش xray را بررسی می‌کند.
    """

    def test_process_is_alive_after_start(
        self,
        xray_process: XrayProcess,
    ) -> None:
        """Ensure managed xray process remains alive.

        زنده بودن پردازش مدیریت‌شده xray را بررسی می‌کند.
        """
        assert xray_process.is_alive() is True

    def test_process_stops_cleanly(self, xray_binary: Path) -> None:
        """Ensure process cleanup works correctly.

        پاک‌سازی صحیح پردازش را بررسی می‌کند.
        """
        with TemporaryDirectory(prefix="bimarz-xray-stop-test-") as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(build_connect_config(), encoding="utf-8")

            process = XrayProcess(
                binary_path=xray_binary,
                config_path=config_path,
            )

            try:
                process.start()
                assert process.is_alive() is True
            finally:
                process.stop()

            assert process.is_alive() is False


@pytest.mark.integration
class TestXrayMultipleOperations:
    """Validate repeated operations against one xray instance.

    عملیات تکراری روی یک نمونه xray را بررسی می‌کند.
    """

    @pytest.mark.asyncio
    async def test_multiple_outbound_operations(
        self,
        xray_process: XrayProcess,
    ) -> None:
        """Verify multiple outbound lifecycle operations.

        چرخه چند outbound را بررسی می‌کند.
        """
        _skip_if_engine_missing()

        client_class = get_engine_client_class()
        client = await connect_with_retry(
            client_class,
            endpoint=f"http://{TEST_XRAY_HOST}:{TEST_XRAY_API_PORT}",
            max_retries=10,
            delay=0.5,
        )

        outbound_tags = [
            "bimarz-test-outbound-1",
            "bimarz-test-outbound-2",
            "bimarz-test-outbound-3",
        ]

        try:
            for tag in outbound_tags:
                await client.add_vless_reality_outbound(
                    tag=tag,
                    uuid=TEST_UUID,
                    flow="xtls-rprx-vision",
                    address="127.0.0.1",
                    port=1,
                    network="tcp",
                    sni="localhost",
                    fingerprint="chrome",
                    public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                    short_id_hex="",
                    spider_x="/",
                )

            for tag in outbound_tags:
                result = await client.get_outbound_stats(tag)
                assert result[0] == tag
                assert isinstance(result[1], int)
                assert isinstance(result[2], int)

        finally:
            # Cleanup created outbounds
            # پاک‌سازی outboundهای ساخته‌شده
            for tag in outbound_tags:
                with contextlib.suppress(Exception):
                    await client.remove_outbound(tag)

            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result


@pytest.mark.integration
def test_xray_port_is_numeric() -> None:
    """Validate API port configuration.

    مقدار پورت API را بررسی می‌کند.
    """
    assert isinstance(TEST_XRAY_API_PORT, int)
    assert 1 <= TEST_XRAY_API_PORT <= 65535


@pytest.mark.integration
def test_xray_host_resolves() -> None:
    """Validate local host resolution.

    resolve شدن hostname محلی را بررسی می‌کند.
    """
    socket.gethostbyname(TEST_XRAY_HOST)


@pytest.mark.integration
class TestXrayGrpcBoundary:
    """Validate Python -> Rust -> gRPC serialization boundary.

    مرز سریال‌سازی Python، Rust و gRPC را بررسی می‌کند.
    """

    @pytest.mark.asyncio
    async def test_invalid_outbound_data_is_rejected(
        self,
        xray_process: XrayProcess,
    ) -> None:
        """Ensure invalid outbound configuration is rejected.

        رد شدن تنظیمات نامعتبر outbound را بررسی می‌کند.
        """
        _skip_if_engine_missing()

        client_class = get_engine_client_class()
        client = await connect_with_retry(
            client_class,
            endpoint=f"http://{TEST_XRAY_HOST}:{TEST_XRAY_API_PORT}",
            max_retries=10,
            delay=0.5,
        )

        try:
            with pytest.raises((ValueError, RuntimeError, OSError)):
                await client.add_vless_reality_outbound(
                    tag="",
                    uuid=TEST_UUID,
                    flow="xtls-rprx-vision",
                    address="",
                    port=0,
                    network="tcp",
                    sni="",
                    fingerprint="chrome",
                    public_key_b64="",
                    short_id_hex="",
                    spider_x="/",
                )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result


@pytest.mark.integration
class TestXrayCleanup:
    """Validate cleanup behavior after failed operations.

    رفتار پاک‌سازی بعد از عملیات ناموفق را بررسی می‌کند.
    """

    @pytest.mark.asyncio
    async def test_failed_operation_does_not_leave_outbound(
        self,
        xray_process: XrayProcess,
    ) -> None:
        """Ensure failed operations do not pollute xray state.

        اطمینان از باقی نماندن outbound خراب در وضعیت xray.
        """
        _skip_if_engine_missing()

        client_class = get_engine_client_class()
        client = await connect_with_retry(
            client_class,
            endpoint=f"http://{TEST_XRAY_HOST}:{TEST_XRAY_API_PORT}",
            max_retries=10,
            delay=0.5,
        )

        tag = "bimarz-cleanup-check"

        try:
            # Invalid operation MUST fail
            # عملیات نامعتبر باید حتماً شکست بخورد
            with pytest.raises((ValueError, RuntimeError, OSError)):
                await client.add_vless_reality_outbound(
                    tag=tag,
                    uuid=TEST_UUID,
                    flow="xtls-rprx-vision",
                    address="",
                    port=0,
                    network="tcp",
                    sni="",
                    fingerprint="chrome",
                    public_key_b64="",
                    short_id_hex="",
                    spider_x="/",
                )

            # After failure, a subsequent valid add + remove must still work
            # بعد از failure، عملیات معتبر بعدی باید همچنان کار کند
            try:
                await client.add_vless_reality_outbound(
                    tag=tag,
                    uuid=TEST_UUID,
                    flow="xtls-rprx-vision",
                    address="127.0.0.1",
                    port=1,
                    network="tcp",
                    sni="localhost",
                    fingerprint="chrome",
                    public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                    short_id_hex="",
                    spider_x="/",
                )
            finally:
                with contextlib.suppress(Exception):
                    await client.remove_outbound(tag)

        finally:
            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result
