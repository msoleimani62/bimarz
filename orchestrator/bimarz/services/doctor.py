"""
Environment diagnostics service.
"""

from __future__ import annotations

import logging

from bimarz.config import AppConfig
from bimarz.constants import BIMARZ_VERSION
from bimarz.engine import (
    EngineNotBuiltError,
    probe_grpc_with_engine,
)
from bimarz.killswitch_manager import KillSwitchManager
from bimarz.models import DoctorReport, GrpcStatus
from bimarz.platform_detect import detect_environment
from bimarz.profiles import ProfileStore
from bimarz.xray_manager import (
    BinaryNotFoundError,
    XrayManagerError,
    find_xray_binary,
    get_xray_version,
    probe_tcp_port,
)

logger = logging.getLogger(__name__)


class DoctorService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def run(self, xray_bin: str | None = None, timeout: float | None = None) -> DoctorReport:
        """Run full environment diagnostics and return a structured report."""
        report = DoctorReport(
            bimarz_version=BIMARZ_VERSION,
            environment=detect_environment(),
            xray_binary_found=False,
            xray_binary_path=None,
            xray_version=None,
            grpc_status=GrpcStatus.not_checked,
            grpc_endpoint="",
            profiles_count=0,
            killswitch_active=False,
        )

        try:
            found_path = (
                find_xray_binary(xray_bin) if xray_bin else find_xray_binary()
            )
            report.xray_binary_path = str(found_path)
            report.xray_binary_found = True
            try:
                report.xray_version = get_xray_version(found_path)
            except XrayManagerError:
                report.xray_version = None
        except BinaryNotFoundError:
            report.xray_binary_found = False

        # ProfileStore may be unreadable (wrong password, corrupted file, etc.)
        # ProfileStore ممکن است غیرقابل خواندن باشد (پسورد اشتباه، فایل خراب و غیره)
        try:
            store = ProfileStore()
            report.profiles_count = len(store.list_profiles())
        except Exception as exc:
            logger.debug("ProfileStore read failed: %s", exc)
            report.profiles_count = 0

        ks = KillSwitchManager()
        report.killswitch_active = ks.state.active

        # Only fall back to config default when caller did not pass a value at all.
        # فقط وقتی به مقدار پیش‌فرض برمی‌گردیم که فراخوان اصلاً مقداری نداده باشد.
        t = self.config.doctor_timeout if timeout is None else timeout
        host = self.config.grpc_host
        port = self.config.grpc_port
        # Always store the full URI so the rest of the codebase has a single format.
        # همیشه URI کامل را نگه می‌داریم تا بقیه‌ی کدبیس یک فرمت واحد داشته باشد.
        report.grpc_endpoint = f"http://{host}:{port}"

        # TCP probe may raise on restricted networks; treat any exception as "unreachable".
        # پروب TCP ممکن است در شبکه‌های محدود استثنا پرتاب کند؛ هر استثنایی را «غیرقابل‌دسترس» می‌گیریم.
        try:
            tcp_ok = await probe_tcp_port(host, port, timeout=t)
        except Exception as exc:
            logger.debug("TCP probe failed: %s", exc)
            tcp_ok = False

        if not tcp_ok:
            report.grpc_status = GrpcStatus.unreachable
        else:
            try:
                grpc_ok = await probe_grpc_with_engine(report.grpc_endpoint, timeout=t)
                report.grpc_status = (
                    GrpcStatus.responding if grpc_ok else GrpcStatus.listening
                )
            except EngineNotBuiltError:
                report.grpc_status = GrpcStatus.listening
            except Exception as exc:
                logger.debug("gRPC probe failed: %s", exc)
                report.grpc_status = GrpcStatus.listening

        return report
