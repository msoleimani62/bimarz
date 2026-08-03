"""
xray-core process lifecycle service.
سرویس مدیریت چرخه عمر فرآیند xray-core.
"""

from __future__ import annotations

from bimarz.models import ServerProfile
from bimarz.protocols import BinaryFinder, ConfigBuilder, ProcessFactory
from bimarz.xray_config import build_connect_config
from bimarz.xray_manager import BinaryNotFoundError, XrayProcess, find_xray_binary


class ProcessService:
    def __init__(
        self,
        binary_finder: BinaryFinder | None = None,
        config_builder: ConfigBuilder | None = None,
        process_factory: ProcessFactory | None = None,
    ) -> None:
        self.binary_finder = binary_finder or find_xray_binary
        self.config_builder = config_builder or build_connect_config
        self.process_factory = process_factory or (
            lambda binary, config: XrayProcess(binary, config)
        )
        self._proc: XrayProcess | None = None

    def start(self, profile: ServerProfile) -> XrayProcess:
        """Start xray-core process for the given profile.
        فرآیند xray-core را برای پروفایل داده‌شده راه‌اندازی می‌کند.
        توجه: کانفیگ پایه بدون profile ساخته می‌شود؛ پروفایل بعداً از طریق gRPC تزریق می‌شود.
        Note: base config is built without profile; profile is injected later via gRPC.
        """
        binary = self.binary_finder()
        if binary is None:
            raise BinaryNotFoundError("xray-core binary not found")
        # Matches real signature of build_connect_config (all params optional)
        # مطابق با امضای واقعی build_connect_config (همه پارامترها اختیاری)
        config = self.config_builder(enable_dns_guard=True)
        proc = self.process_factory(str(binary), config)
        proc.start()
        self._proc = proc
        return proc

    def stop(self) -> None:
        """Stop the running xray process if any.
        در صورت وجود فرآیند xray در حال اجرا را متوقف می‌کند.
        """
        if self._proc is not None and self._proc.is_running():
            self._proc.stop()
        self._proc = None

    @property
    def process(self) -> XrayProcess | None:
        return self._proc
