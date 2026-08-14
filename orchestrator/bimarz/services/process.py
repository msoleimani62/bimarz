"""
xray-core process lifecycle service.

Provides explicit process and runtime-directory ownership.

سرویس چرخه عمر فرآیند xray-core.

مالکیت صریح فرآیند و دایرکتوری runtime را مدیریت می‌کند.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path

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
            lambda binary, config: XrayProcess(
                Path(binary),
                Path(config),
            )
        )
        self._proc: XrayProcess | None = None
        self._runtime_dir: tempfile.TemporaryDirectory | None = None

    def start(self, profile: ServerProfile) -> XrayProcess:
        """Start xray-core and acquire process ownership.

        راه‌اندازی xray-core و به‌دست گرفتن مالکیت فرآیند.
        """
        if self._proc is not None:
            return self._proc

        binary = self.binary_finder()
        if binary is None:
            raise BinaryNotFoundError("xray-core binary not found")

        runtime_dir = tempfile.TemporaryDirectory()
        self._runtime_dir = runtime_dir

        try:
            config_path = Path(runtime_dir.name) / "connect-runtime.json"
            config = self.config_builder(enable_dns_guard=True)
            config_path.write_text(config, encoding="utf-8")

            with contextlib.suppress(Exception):
                config_path.chmod(0o600)

            proc = self.process_factory(binary, config_path)
            proc.start()

            self._proc = proc
            return proc

        except Exception:
            self._proc = None
            self._cleanup_runtime()
            raise

    def stop(self) -> None:
        """Stop the process and always release runtime ownership.

        توقف فرآیند و آزادسازی قطعی مالکیت runtime.
        """
        proc = self._proc
        self._proc = None

        try:
            if proc is not None:
                proc.stop()
        finally:
            self._cleanup_runtime()

    def _cleanup_runtime(self) -> None:
        """Remove the temporary runtime directory.

        حذف دایرکتوری موقت runtime.
        """
        runtime_dir = self._runtime_dir
        self._runtime_dir = None

        if runtime_dir is not None:
            runtime_dir.cleanup()

    @property
    def process(self) -> XrayProcess | None:
        return self._proc
