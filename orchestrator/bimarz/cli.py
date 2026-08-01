#!/usr/bin/env python3
"""
CLI entry-point for bimarz.
نقطه ورود CLI برای bimarz.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import uuid
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, NoReturn, Protocol, TypedDict, cast
from urllib.parse import parse_qs, unquote, urlparse

from rich.console import Console

from bimarz.constants import (
    ACTIVE_OUTBOUND_TAG,
    BIMARZ_VERSION,
    DEFAULT_GRPC_HOST,
    DEFAULT_GRPC_PORT,
    DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR,
    DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS,
    ENGINE_CONNECT_MAX_RETRIES,
    ENGINE_CONNECT_RETRY_DELAY,
    FAILOVER_CHECK_INTERVAL_SECONDS,
)
from bimarz.engine import (
    EngineNotBuiltError,
    get_engine_client_class,
    probe_grpc_with_engine,
)
from bimarz.failover import FailoverManager, check_profile_health
from bimarz.killswitch_manager import KillSwitchManager
from bimarz.models import DoctorReport, GrpcStatus, ServerProfile
from bimarz.platform_detect import detect_environment
from bimarz.profiles import ProfileStore
from bimarz.xray_config import build_connect_config
from bimarz.xray_manager import (
    BinaryNotFoundError,
    XrayManagerError,
    XrayProcess,
    find_xray_binary,
    get_xray_version,
    probe_tcp_port,
)

console = Console()
logger = logging.getLogger("bimarz.cli")


# ---------------------------------------------------------------------------
# Configuration Layer
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AppConfig:
    """Central configuration holder.
    نگهدارنده مرکزی تنظیمات.
    اولویت: Environment Variable > مقدار پیش‌فرض.
    """
    grpc_host: str = DEFAULT_GRPC_HOST
    grpc_port: int = DEFAULT_GRPC_PORT
    doctor_timeout: float = DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS
    engine_retries: int = ENGINE_CONNECT_MAX_RETRIES
    engine_retry_delay: float = ENGINE_CONNECT_RETRY_DELAY
    failover_interval: float = FAILOVER_CHECK_INTERVAL_SECONDS
    default_interface: str = "tun0"
    log_level: int = logging.WARNING

    @classmethod
    def from_env(cls) -> AppConfig:
        """Build config from environment variables when present.
        تنظیمات را از متغیرهای محیطی می‌سازد (در صورت وجود).
        در برابر مقادیر نامعتبر مقاوم است.
        """
        def _get_int(name: str, default: int) -> int:
            val = os.getenv(name)
            if val is None:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        def _get_float(name: str, default: float) -> float:
            val = os.getenv(name)
            if val is None:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        return cls(
            grpc_host=os.getenv("BIMARZ_GRPC_HOST", DEFAULT_GRPC_HOST),
            grpc_port=_get_int("BIMARZ_GRPC_PORT", DEFAULT_GRPC_PORT),
            doctor_timeout=_get_float("BIMARZ_DOCTOR_TIMEOUT", DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS),
            engine_retries=_get_int("BIMARZ_ENGINE_RETRIES", ENGINE_CONNECT_MAX_RETRIES),
            engine_retry_delay=_get_float("BIMARZ_ENGINE_RETRY_DELAY", ENGINE_CONNECT_RETRY_DELAY),
            failover_interval=_get_float("BIMARZ_FAILOVER_INTERVAL", FAILOVER_CHECK_INTERVAL_SECONDS),
            default_interface=os.getenv("BIMARZ_DEFAULT_INTERFACE", "tun0"),
        )


# ---------------------------------------------------------------------------
# TypedDict for outbound
# ---------------------------------------------------------------------------

class VlessOutbound(TypedDict, total=False):
    protocol: str
    address: str
    port: int
    id: str
    flow: str
    security: str
    sni: str
    fp: str
    publicKey: str
    shortId: str
    spiderX: str
    encryption: str
    type: str
    path: str
    host: str
    serviceName: str
    authority: str
    mode: str
    alpn: str
    headerType: str
    seed: str
    packetEncoding: str
    fragment: str
    mux: str
    allowInsecure: bool
    ech: str
    echForceQuery: str
    pqv: str


# ---------------------------------------------------------------------------
# Event System with typed payloads
# ---------------------------------------------------------------------------

class ConnectionEvent(Enum):
    STARTED = auto()
    ENGINE_READY = auto()
    KILLSWITCH_ENABLED = auto()
    FAILOVER_TRIGGERED = auto()
    KILLSWITCH_WATCHER_DIED = auto()
    PROCESS_STOPPED = auto()
    CLEANUP_DONE = auto()
    ERROR = auto()


class EventPayload(TypedDict, total=False):
    profile_id: str
    new_profile_id: str
    error: str
    message: str


EventHandler = Callable[[ConnectionEvent, EventPayload], None]


# ---------------------------------------------------------------------------
# Engine Protocol
# ---------------------------------------------------------------------------

class EngineClient(Protocol):
    def add_vless_reality_outbound(self, **kwargs: Any) -> None: ...
    def remove_outbound(self, tag: str) -> None: ...


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

BinaryFinder = Callable[[], Path | str | None]
ConfigBuilder = Callable[[ServerProfile, bool], Any]
ProcessFactory = Callable[[str, Any], XrayProcess]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_current_uid() -> int | None:
    """Return current user UID when available.
    شناسه کاربری فعلی را در صورت وجود برمی‌گرداند.
    """
    if hasattr(os, "getuid"):
        return os.getuid()
    return None


def _get_outbound(profile: ServerProfile) -> dict[str, Any]:
    return getattr(profile, "outbound", None) or {}


def _format_profile_address(profile: ServerProfile) -> str:
    outbound = _get_outbound(profile)
    return str(outbound.get("address", "?"))


def _outbound_kwargs(profile: ServerProfile) -> dict[str, Any]:
    outbound = _get_outbound(profile)
    return {
        "tag": ACTIVE_OUTBOUND_TAG,
        "address": outbound.get("address", ""),
        "port": int(outbound.get("port", 443)),
        "id": outbound.get("id", ""),
        "flow": outbound.get("flow", "xtls-rprx-vision"),
        "security": outbound.get("security", "reality"),
        "sni": outbound.get("sni", ""),
        "fp": outbound.get("fp", "chrome"),
        "pbk": outbound.get("publicKey", ""),
        "sid": outbound.get("shortId", ""),
        "spx": outbound.get("spiderX", ""),
        "network": outbound.get("type", "tcp"),
        "path": outbound.get("path", ""),
        "serviceName": outbound.get("serviceName", ""),
        "authority": outbound.get("authority", ""),
        "mode": outbound.get("mode", ""),
        "alpn": outbound.get("alpn", ""),
        "packetEncoding": outbound.get("packetEncoding", ""),
        "fragment": outbound.get("fragment", ""),
        "mux": outbound.get("mux", ""),
        "allowInsecure": outbound.get("allowInsecure", False),
        "ech": outbound.get("ech", ""),
    }


def _profiles_by_id(profiles: list[ServerProfile]) -> dict[str, ServerProfile]:
    return {p.profile_id: p for p in profiles}


# ---------------------------------------------------------------------------
# VLESS Parser
# ---------------------------------------------------------------------------

def _parse_vless_link(link: str) -> ServerProfile:
    link = link.strip()
    if not link.startswith("vless://"):
        raise ValueError("Only vless:// links are supported")

    parsed = urlparse(link)
    if not parsed.hostname:
        raise ValueError("Invalid VLESS link: missing host")

    raw_uuid = unquote(parsed.username or "")
    if not raw_uuid:
        raise ValueError("Invalid VLESS link: missing UUID")

    try:
        uuid.UUID(raw_uuid)
    except ValueError as exc:
        raise ValueError(f"Invalid UUID in VLESS link: {raw_uuid}") from exc

    port = parsed.port or 443
    query = parse_qs(parsed.query)

    def _q(key: str, default: str = "") -> str:
        vals = query.get(key)
        return vals[0] if vals else default

    def _qb(key: str, default: bool = False) -> bool:
        val = _q(key, "").lower()
        if val in ("1", "true", "yes", "on"):
            return True
        if val in ("0", "false", "no", "off"):
            return False
        return default

    name = unquote(parsed.fragment) if parsed.fragment else f"{parsed.hostname}:{port}"
    profile_id = uuid.uuid4().hex

    outbound: VlessOutbound = {
        "protocol": "vless",
        "address": parsed.hostname or "",
        "port": port,
        "id": raw_uuid,
        "flow": _q("flow", "xtls-rprx-vision"),
        "security": _q("security", "reality"),
        "sni": _q("sni", _q("host", "")),
        "fp": _q("fp", "chrome"),
        "publicKey": _q("pbk", ""),
        "shortId": _q("sid", ""),
        "spiderX": _q("spx", ""),
        "encryption": _q("encryption", "none"),
        "type": _q("type", "tcp"),
        "path": _q("path", ""),
        "host": _q("host", ""),
        "serviceName": _q("serviceName", ""),
        "authority": _q("authority", ""),
        "mode": _q("mode", ""),
        "alpn": _q("alpn", ""),
        "headerType": _q("headerType", ""),
        "seed": _q("seed", ""),
        "packetEncoding": _q("packetEncoding", ""),
        "fragment": _q("fragment", ""),
        "mux": _q("mux", ""),
        "allowInsecure": _qb("allowInsecure", False),
        "ech": _q("ech", ""),
        "echForceQuery": _q("echForceQuery", ""),
        "pqv": _q("pqv", ""),
    }

    return ServerProfile(
        profile_id=profile_id,
        name=name,
        outbound=dict(outbound),
    )


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    try:
        import grpc  # type: ignore
        if isinstance(exc, grpc.RpcError):
            code = exc.code()
            return code in (
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                grpc.StatusCode.RESOURCE_EXHAUSTED,
            )
    except ImportError:
        pass
    return False


async def _connect_with_retry(
    engine_client_class: type,
    max_retries: int,
    delay: float,
) -> EngineClient:
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return engine_client_class()  # type: ignore[return-value]
        except Exception as exc:
            if _is_retryable(exc):
                last_exc = exc
                logger.debug("Engine connect attempt %d/%d failed: %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to connect to engine after retries")


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class DoctorService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def run(self, xray_bin: str | None = None, timeout: float | None = None) -> DoctorReport:
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

        store = ProfileStore()
        report.profiles_count = len(store.list_profiles())

        ks = KillSwitchManager()
        report.killswitch_active = ks.state.active

        t = timeout or self.config.doctor_timeout
        host = self.config.grpc_host
        port = self.config.grpc_port
        report.grpc_endpoint = f"{host}:{port}"

        tcp_ok = await probe_tcp_port(host, port, timeout=t)
        if not tcp_ok:
            report.grpc_status = GrpcStatus.unreachable
        else:
            try:
                engine_class = get_engine_client_class()
                engine = engine_class()
                grpc_ok = await probe_grpc_with_engine(engine, timeout=t)
                report.grpc_status = (
                    GrpcStatus.responding if grpc_ok else GrpcStatus.listening
                )
            except EngineNotBuiltError:
                report.grpc_status = GrpcStatus.listening
            except Exception as exc:
                logger.debug("gRPC probe failed: %s", exc)
                report.grpc_status = GrpcStatus.listening

        return report


class ProfileService:
    def __init__(self, store: ProfileStore | None = None) -> None:
        self.store = store or ProfileStore()

    def add_from_link(self, link: str) -> ServerProfile:
        profile = _parse_vless_link(link)
        self.store.add_profile(profile)
        return profile

    def list_profiles(self) -> list[ServerProfile]:
        return self.store.list_profiles()

    def remove(self, profile_id: str) -> None:
        self.store.remove_profile(profile_id)

    def get(self, profile_id: str) -> ServerProfile | None:
        return self.store.get_profile(profile_id)


class HealthService:
    def __init__(self, store: ProfileStore | None = None) -> None:
        self.store = store or ProfileStore()

    async def check_all(self) -> list[tuple[ServerProfile, Any]]:
        profiles = self.store.list_profiles()
        if not profiles:
            return []
        tasks = [check_profile_health(p) for p in profiles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(zip(profiles, results))


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
        binary = self.binary_finder()
        if binary is None:
            raise BinaryNotFoundError("xray-core binary not found")
        config = self.config_builder(enable_dns_guard=True)
        proc = self.process_factory(str(binary), config)
        proc.start()
        self._proc = proc
        return proc

    def stop(self) -> None:
        if self._proc is not None and self._proc.is_running():
            self._proc.stop()
        self._proc = None

    @property
    def process(self) -> XrayProcess | None:
        return self._proc


class EngineService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._engine: EngineClient | None = None

    async def connect(self) -> EngineClient:
        engine_class = get_engine_client_class()
        engine = await _connect_with_retry(
            engine_class,
            max_retries=self.config.engine_retries,
            delay=self.config.engine_retry_delay,
        )
        self._engine = engine
        return engine

    def add_outbound(self, profile: ServerProfile) -> None:
        if self._engine is None:
            raise RuntimeError("Engine not connected")
        self._engine.add_vless_reality_outbound(**_outbound_kwargs(profile))

    def remove_outbound(self, tag: str = ACTIVE_OUTBOUND_TAG) -> None:
        if self._engine is None:
            return
        try:
            self._engine.remove_outbound(tag)
        except Exception as exc:
            logger.warning("remove_outbound failed: %s", exc)

    @property
    def engine(self) -> EngineClient | None:
        return self._engine


class KillSwitchService:
    def __init__(self, manager: KillSwitchManager | None = None) -> None:
        self.manager = manager or KillSwitchManager()

    def enable(self, interface: str = "tun0", uid: int | None = None) -> None:
        if uid is None:
            uid = _get_current_uid()
        self.manager.activate(interface=interface, xray_uid=uid)

    def disable(self) -> None:
        self.manager.deactivate()

    def is_active(self) -> bool:
        return self.manager.state.active

    def is_watcher_alive(self) -> bool:
        return self.manager.is_watcher_alive()


class FailoverService:
    def __init__(self, initial_profile_id: str) -> None:
        self.manager = FailoverManager(initial_profile_id)

    def record(self, health: Any) -> None:
        self.manager.record_result(health)

    def should_trigger(self) -> bool:
        return self.manager.should_trigger()

    def pick_best(self, profiles: list[ServerProfile]) -> ServerProfile | None:
        return self.manager.pick_best_alternative(profiles)

    def trigger(self, profile_id: str) -> None:
        self.manager.trigger_failover(profile_id)

    @property
    def active_id(self) -> str:
        return self.manager.active_profile_id


# ---------------------------------------------------------------------------
# ConnectionService (Context Manager – single cleanup & error owner)
# ---------------------------------------------------------------------------

class ConnectionService:
    """High-level connection orchestrator.
    orchestrator سطح بالای اتصال.
    فقط __aexit__ مسئول cleanup و انتشار ERROR است.
    """

    def __init__(
        self,
        config: AppConfig,
        process_svc: ProcessService | None = None,
        engine_svc: EngineService | None = None,
        ks_svc: KillSwitchService | None = None,
        event_handler: EventHandler | None = None,
    ) -> None:
        self.config = config
        self.process_svc = process_svc or ProcessService()
        self.engine_svc = engine_svc or EngineService(config)
        self.ks_svc = ks_svc or KillSwitchService()
        self._event_handler = event_handler
        self._stop_event = asyncio.Event()
        self._cleaned = False
        self._signals_registered: list[signal.Signals] = []

    def _emit(self, event: ConnectionEvent, **data: Any) -> None:
        payload = cast(EventPayload, data)
        if self._event_handler:
            self._event_handler(event, payload)
        logger.debug("Event %s: %s", event.name, data)

    async def __aenter__(self) -> ConnectionService:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Only __aexit__ is responsible for emitting ERROR
        # فقط __aexit__ مسئول انتشار ERROR است
        if exc is not None and not isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
            self._emit(ConnectionEvent.ERROR, error=str(exc))
        await self.cleanup()

    def _register_signals(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGHUP):
            try:
                loop.add_signal_handler(sig, self._stop_event.set)
                self._signals_registered.append(sig)
            except (NotImplementedError, RuntimeError) as exc:
                logger.debug("Signal handler unavailable for %s: %s", sig, exc)

    def _unregister_signals(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in self._signals_registered:
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, RuntimeError, ValueError):
                pass
        self._signals_registered.clear()

    async def start(
        self,
        profile: ServerProfile,
        *,
        auto_failover: bool = False,
        killswitch: bool = False,
        all_profiles: list[ServerProfile] | None = None,
    ) -> None:
        """Start connection and monitoring.
        Cleanup and ERROR emission are owned exclusively by __aexit__.
        اتصال و نظارت را شروع می‌کند.
        cleanup و انتشار ERROR منحصراً توسط __aexit__ انجام می‌شود.
        """
        self._emit(ConnectionEvent.STARTED, profile_id=profile.profile_id)

        proc = self.process_svc.start(profile)
        await self.engine_svc.connect()
        self.engine_svc.add_outbound(profile)
        self._emit(ConnectionEvent.ENGINE_READY)

        if killswitch:
            self.ks_svc.enable(interface=self.config.default_interface)
            self._emit(ConnectionEvent.KILLSWITCH_ENABLED)

        self._register_signals()

        if auto_failover and all_profiles:
            await self._failover_loop(profile, all_profiles, proc)
        else:
            await self._watch_loop(proc)

    async def _failover_loop(
        self,
        initial: ServerProfile,
        all_profiles: list[ServerProfile],
        proc: XrayProcess,
    ) -> None:
        failover = FailoverService(initial.profile_id)
        profile_map = _profiles_by_id(all_profiles)
        active = initial

        while not self._stop_event.is_set() and proc.is_running():
            if failover.active_id in profile_map:
                active = profile_map[failover.active_id]

            health = await check_profile_health(active)
            failover.record(health)

            if failover.should_trigger():
                best = failover.pick_best(list(profile_map.values()))
                if best is None:
                    logger.error("No alternative profile available")
                    break

                self.engine_svc.remove_outbound()
                self.engine_svc.add_outbound(best)
                failover.trigger(best.profile_id)
                active = best
                self._emit(ConnectionEvent.FAILOVER_TRIGGERED, new_profile_id=best.profile_id)

            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(ConnectionEvent.KILLSWITCH_WATCHER_DIED)
                break

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.failover_interval,
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _watch_loop(self, proc: XrayProcess) -> None:
        while not self._stop_event.is_set() and proc.is_running():
            if self.ks_svc.is_active() and not self.ks_svc.is_watcher_alive():
                self._emit(ConnectionEvent.KILLSWITCH_WATCHER_DIED)
                break
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=1.0)
                break
            except asyncio.TimeoutError:
                continue

    async def cleanup(self) -> None:
        """Idempotent cleanup.
        پاک‌سازی idempotent.
        """
        if self._cleaned:
            return
        self._cleaned = True

        self._unregister_signals()
        self.process_svc.stop()
        self._emit(ConnectionEvent.PROCESS_STOPPED)

        if self.ks_svc.is_active():
            self.ks_svc.disable()

        self._emit(ConnectionEvent.CLEANUP_DONE)

    def request_stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# CLI Handlers
# ---------------------------------------------------------------------------

def _render_doctor_report(report: DoctorReport) -> None:
    console.print(f"[bold]bimarz doctor[/bold] — version {BIMARZ_VERSION}")

    if report.xray_binary_found:
        version_suffix = f" (version: {report.xray_version})" if report.xray_version else ""
        console.print(f"[green]✓[/green] xray-core binary found: {report.xray_binary_path}{version_suffix}")
    else:
        console.print("[red]✗[/red] xray-core binary not found")
        console.print("[yellow]hint:[/yellow] install xray-core or use --xray-bin /path/to/xray")

    status_colour = {
        GrpcStatus.not_checked: "dim",
        GrpcStatus.unreachable: "red",
        GrpcStatus.listening: "yellow",
        GrpcStatus.responding: "green",
    }.get(report.grpc_status, "white")

    console.print(
        f"[{status_colour}]●[/{status_colour}] gRPC status: {report.grpc_status.value} "
        f"at {report.grpc_endpoint}"
    )

    if report.grpc_status == GrpcStatus.unreachable:
        console.print("[yellow]hint:[/yellow] ensure xray-core is running and the API port is open.")
    elif report.grpc_status == GrpcStatus.listening:
        console.print(
            "[yellow]hint:[/yellow] TCP port is open but no valid gRPC response. "
            "If the Rust extension is not built, run: "
            "source .venv/bin/activate && maturin develop --release"
        )
    elif report.grpc_status == GrpcStatus.responding:
        console.print("[green]✓[/green] gRPC API is fully responsive")

    console.print(f"Profiles stored: {report.profiles_count}")

    if report.killswitch_active:
        console.print("[green]✓[/green] Kill-switch is active")
    else:
        console.print("[dim]○ Kill-switch is inactive[/dim]")


def _make_event_handler() -> EventHandler:
    def handler(event: ConnectionEvent, data: EventPayload) -> None:
        if event == ConnectionEvent.FAILOVER_TRIGGERED:
            console.print(f"[yellow]Failover: switched to {data.get('new_profile_id')}[/yellow]")
        elif event == ConnectionEvent.KILLSWITCH_ENABLED:
            console.print("[green]Kill-switch enabled.[/green]")
        elif event == ConnectionEvent.KILLSWITCH_WATCHER_DIED:
            console.print("[red]Kill-switch watcher died. Stopping tunnel.[/red]")
        elif event == ConnectionEvent.CLEANUP_DONE:
            console.print("[dim]Disconnected.[/dim]")
        elif event == ConnectionEvent.ERROR:
            console.print(f"[red]Error: {data.get('error')}[/red]")
    return handler


def _doctor_timeout_seconds(args: argparse.Namespace) -> float:
    # مهلت زمانی probe doctor را برمی‌گرداند: آرگومان CLI > متغیر محیطی > مقدار پیش‌فرض
    # resolve the doctor probe timeout: CLI flag > environment variable > default
    if getattr(args, "doctor_timeout", None) is not None:
        return args.doctor_timeout
    env_val = os.getenv(DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR)
    if env_val is not None:
        try:
            return float(env_val)
        except ValueError:
            pass
    return DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS


async def _run_doctor_async(args: argparse.Namespace, config: AppConfig) -> None:
    svc = DoctorService(config)
    report = await svc.run(xray_bin=args.xray_bin, timeout=_doctor_timeout_seconds(args))
    _render_doctor_report(report)


def _run_doctor(args: argparse.Namespace, config: AppConfig) -> None:
    asyncio.run(_run_doctor_async(args, config))


def _run_profile_add(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    try:
        profile = svc.add_from_link(args.link)
        console.print(
            f"[green]✓[/green] Profile added: {profile.profile_id} "
            f"({_format_profile_address(profile)})"
        )
    except ValueError as exc:
        console.print(f"[red]Invalid link: {exc}[/red]")
        raise SystemExit(1)
    except Exception as exc:
        console.print(f"[red]Failed to add profile: {exc}[/red]")
        raise SystemExit(1)


def _run_profile_list(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    profiles = svc.list_profiles()
    if not profiles:
        console.print("[dim]No profiles saved.[/dim]")
        return
    for profile in profiles:
        addr = _format_profile_address(profile)
        name = getattr(profile, "name", "") or ""
        extra = f" ({name})" if name else ""
        console.print(f"{profile.profile_id}: {addr}{extra}")


def _run_profile_remove(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    try:
        svc.remove(args.profile_id)
        console.print(f"[green]Removed profile {args.profile_id}[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to remove profile: {exc}[/red]")
        raise SystemExit(1)


async def _run_healthcheck_async(args: argparse.Namespace, config: AppConfig) -> None:
    svc = HealthService()
    results = await svc.check_all()
    if not results:
        console.print("[yellow]No profiles to check.[/yellow]")
        return
    for profile, result in results:
        addr = _format_profile_address(profile)
        if isinstance(result, Exception):
            console.print(f"[red]✗[/red] {addr} — error: {result}")
        elif isinstance(result, dict) and result.get("ok"):
            latency = result.get("latency_ms", "?")
            console.print(f"[green]✓[/green] {addr} — {latency}ms")
        else:
            console.print(f"[red]✗[/red] {addr} — unreachable")


def _run_healthcheck(args: argparse.Namespace, config: AppConfig) -> None:
    asyncio.run(_run_healthcheck_async(args, config))


async def _run_connect_async(args: argparse.Namespace, config: AppConfig) -> None:
    profile_svc = ProfileService()
    profile = profile_svc.get(args.profile_id)
    if profile is None:
        console.print(f"[red]Profile '{args.profile_id}' not found.[/red]")
        raise SystemExit(1)

    all_profiles: list[ServerProfile] = []
    if args.auto_failover:
        all_profiles = profile_svc.list_profiles()

    event_handler = _make_event_handler()

    async with ConnectionService(config, event_handler=event_handler) as conn:
        try:
            await conn.start(
                profile,
                auto_failover=args.auto_failover,
                killswitch=args.killswitch,
                all_profiles=all_profiles,
            )
        except KeyboardInterrupt:
            conn.request_stop()
            console.print("\n[yellow]Disconnecting...[/yellow]")


def _run_connect(args: argparse.Namespace, config: AppConfig) -> None:
    try:
        asyncio.run(_run_connect_async(args, config))
    except BinaryNotFoundError:
        console.print(
            "[red]xray-core binary not found. "
            "Run 'bimarz doctor' for diagnostics.[/red]"
        )
        raise SystemExit(1)
    except Exception as exc:
        if args.debug:
            raise
        console.print(f"[red]Connection failed: {exc}[/red]")
        raise SystemExit(1)


def _run_killswitch_enable(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    uid = args.xray_uid if args.xray_uid is not None else _get_current_uid()
    svc.enable(interface=args.interface, uid=uid)
    console.print(f"[green]Kill-switch enabled (xray UID: {uid}).[/green]")


def _run_killswitch_disable(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    svc.disable()
    console.print("[green]Kill-switch disabled.[/green]")


def _run_killswitch_status(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    if svc.is_active():
        console.print("[green]Kill-switch is active[/green]")
    else:
        console.print("[dim]Kill-switch is inactive[/dim]")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bimarz",
        description="Professional management layer for xray-core.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {BIMARZ_VERSION}")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show full technical traceback and enable DEBUG logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Full environment check.")
    doctor_parser.add_argument("--xray-bin", type=str, default=None)
    doctor_parser.add_argument("--doctor-timeout", type=float, default=None)
    doctor_parser.set_defaults(func=_run_doctor)

    profile_parser = subparsers.add_parser("profile", help="Manage server profiles.")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

    p_add = profile_sub.add_parser("add", help="Add a profile from a VLESS share link.")
    p_add.add_argument("link", type=str)
    p_add.set_defaults(func=_run_profile_add)

    p_list = profile_sub.add_parser("list", help="List saved profiles.")
    p_list.set_defaults(func=_run_profile_list)

    p_remove = profile_sub.add_parser("remove", help="Remove a profile by ID.")
    p_remove.add_argument("profile_id", type=str)
    p_remove.set_defaults(func=_run_profile_remove)

    hc = subparsers.add_parser("healthcheck", help="Check all profiles in parallel.")
    hc.set_defaults(func=_run_healthcheck)

    conn = subparsers.add_parser("connect", help="Connect using a profile.")
    conn.add_argument("profile_id", type=str)
    conn.add_argument("--auto-failover", action="store_true")
    conn.add_argument("--killswitch", action="store_true")
    conn.set_defaults(func=_run_connect)

    ks = subparsers.add_parser("killswitch", help="Manage kill-switch independently.")
    ks_sub = ks.add_subparsers(dest="ks_command", required=True)

    ks_en = ks_sub.add_parser("enable", help="Enable kill-switch.")
    ks_en.add_argument("--interface", type=str, default="tun0")
    ks_en.add_argument("--xray-uid", type=int, default=None)
    ks_en.set_defaults(func=_run_killswitch_enable)

    ks_dis = ks_sub.add_parser("disable", help="Disable kill-switch.")
    ks_dis.set_defaults(func=_run_killswitch_disable)

    ks_st = ks_sub.add_parser("status", help="Show kill-switch status.")
    ks_st.set_defaults(func=_run_killswitch_status)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> NoReturn:
    parser = _build_parser()
    args = parser.parse_args()

    config = AppConfig.from_env()
    if getattr(args, "debug", False):
        config.log_level = logging.DEBUG

    logging.basicConfig(level=config.log_level)

    try:
        args.func(args, config)
    except SystemExit:
        raise
    except Exception as exc:
        if getattr(args, "debug", False):
            raise
        console.print(f"[red]Error: {exc}[/red]")
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
