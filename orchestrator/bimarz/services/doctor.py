"""
Environment diagnostics service.
سرویس تشخیص محیط.
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
        """Run full environment diagnostics and return a structured report.
        تشخیص کامل محیط را اجرا کرده و گزارش ساخت‌یافته برمی‌گرداند.
        """
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
            found_path = find_xray_binary(xray_bin) if xray_bin else find_xray_binary()
            report.xray_binary_path = str(found_path)
            report.xray_binary_found = True
            try:
                report.xray_version = get_xray_version(found_path)
            except XrayManagerError:
                report.xray_version = None
        except BinaryNotFoundError:
            report.xray_binary_found = False

        store = ProfileStore()
        report.profiles_count = len(store.list_profiles())

        ks = KillSwitchManager()
        report.killswitch_active = ks.state.active

        t = self.config.doctor_timeout if timeout is None else timeout
        host = self.config.grpc_host
        port = self.config.grpc_port
        report.grpc_endpoint = f"{host}:{port}"

        tcp_ok = await probe_tcp_port(host, port, timeout=t)
        if not tcp_ok:
            report.grpc_status = GrpcStatus.unreachable
        else:
            try:
                grpc_ok = await probe_grpc_with_engine(
                    f"http://{host}:{port}",
                    timeout=t,
                )
                report.grpc_status = GrpcStatus.responding if grpc_ok else GrpcStatus.listening
            except EngineNotBuiltError:
                report.grpc_status = GrpcStatus.listening
            except Exception as exc:
                logger.debug("gRPC probe failed: %s", exc)
                report.grpc_status = GrpcStatus.listening

        return report
