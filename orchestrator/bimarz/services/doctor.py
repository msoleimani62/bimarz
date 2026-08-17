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
    get_xray_proto_version,
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


def _normalize_xray_version(version: str | None) -> str | None:
    """Extract a comparable version token from an xray version string.

    Handles both the binary banner ("Xray 1.8.24 (Xray, ...)") and the
    proto pin tag ("v1.8.24").

    یک توکن نسخه‌ی قابل‌مقایسه از رشته‌ی نسخه‌ی xray استخراج می‌کند. هم
    بنر باینری ("Xray 1.8.24 (Xray, ...)") و هم تگ پین proto ("v1.8.24")
    پشتیبانی می‌شوند.
    """
    if not version:
        return None
    for token in version.split():
        cleaned = token.strip().lstrip("vV")
        if cleaned and cleaned[0].isdigit():
            return cleaned
    return None


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
            if found_path is None:
                raise BinaryNotFoundError("xray-core binary not found")

            report.xray_binary_path = str(found_path)
            report.xray_binary_found = True
            try:
                report.xray_version = get_xray_version(found_path)
            except XrayManagerError:
                report.xray_version = None
        except BinaryNotFoundError:
            report.xray_binary_found = False

        # اگر باینری xray با نسخه‌ی protoای که اکستنشن Rust با آن ساخته شده
        # هماهنگ نباشد، صریحاً هشدار می‌دهیم — ترکیب ناسازگار هرگز نباید
        # بی‌صدا رد شود.
        # Warn explicitly when the xray binary does not match the proto
        # version the Rust extension was built against — an incompatible
        # combination must never pass silently.
        proto_tag = get_xray_proto_version()
        binary_version = _normalize_xray_version(report.xray_version)
        proto_version = _normalize_xray_version(proto_tag)
        if binary_version and proto_version and binary_version != proto_version:
            report.warnings.append(
                f"xray binary version ({report.xray_version}) does not match the proto "
                f"bindings built into the extension ({proto_tag}); rebuild after aligning "
                f"engine-core/xray-proto-pin.env or use the matching xray-core release."
            )

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
