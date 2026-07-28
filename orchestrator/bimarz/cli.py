"""CLI entry point (argparse-based).

This is the ONLY place in the codebase allowed to call sys.exit() — the
same boundary rule used by open-downloader-cli's cli.py. Every other
module raises exceptions; this module catches them and decides the exit
code and the message shown to the user.

نقطه‌ی ورود CLI (مبتنی بر argparse).

این تنها جای مجاز در کل کدبیس برای صدا زدن sys.exit() است — همان قانون
مرزی که در cli.py پروژه‌ی open-downloader-cli استفاده شده. هر ماژول دیگر
استثنا پرتاب می‌کند؛ این ماژول آن‌ها را می‌گیرد و کد خروج و پیام نمایش‌ داده
شده به کاربر را تصمیم می‌گیرد.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from bimarz.constants import (
    BIMARZ_VERSION,
    CONFIG_DIR,
    DEFAULT_GRPC_ENDPOINT,
    DEFAULT_LOCAL_SOCKS_PORT,
    DEFAULT_XRAY_BINARY,
    GRPC_CONNECT_RETRY_ATTEMPTS,
    GRPC_CONNECT_RETRY_DELAY_SECONDS,
    PROFILES_FILE,
)
from bimarz.engine import EngineNotBuiltError, get_engine_client_class
from bimarz.models import DoctorReport, ServerProfile
from bimarz.platform_detect import detect_environment
from bimarz.profiles import ProfileStore, ProfileStoreError
from bimarz.state import console
from bimarz.subscription import SubscriptionParseError, parse_vless_link
from bimarz.xray_config import build_connect_config
from bimarz.xray_manager import (
    BinaryNotFoundError,
    XrayManagerError,
    XrayProcess,
    find_xray_binary,
    get_xray_version,
)


def _run_doctor(args: argparse.Namespace) -> int:
    """Implements `bimarz doctor`: collect a DoctorReport, then render it.

    پیاده‌سازی `bimarz doctor`: یک DoctorReport جمع‌آوری می‌کند، سپس نمایشش
    می‌دهد.
    """
    environment = detect_environment()
    binary_path = find_xray_binary(explicit_path=args.xray_bin)

    xray_version: str | None = None
    warnings: list[str] = []

    if binary_path is None:
        warnings.append(
            "xray-core binary not found. Install it and either add it to "
            "PATH or pass --xray-bin explicitly."
        )
    else:
        try:
            xray_version = get_xray_version(binary_path)
        except XrayManagerError as exc:
            warnings.append(f"found xray-core binary but could not read its version: {exc}")

    # عمداً پروفایل‌ها اینجا رمزگشایی نمی‌شوند — doctor باید بدون پرسیدن
    # پسورد و بدون تعامل اجرا شود؛ فقط وجود فایل را گزارش می‌کند.
    # Profiles are deliberately NOT decrypted here — doctor must run
    # non-interactively without asking for a password; it only reports
    # whether the profiles file exists.
    profiles_file_exists = PROFILES_FILE.exists()

    report = DoctorReport(
        bimarz_version=BIMARZ_VERSION,
        environment=environment,
        xray_binary_found=binary_path is not None,
        xray_binary_path=str(binary_path) if binary_path else None,
        xray_version=xray_version,
        # آزمایش gRPC هنوز در این فاز پیاده نشده؛ صادقانه False گزارش می‌شود.
        # gRPC probing is not implemented yet at this phase; honestly
        # reported as False.
        grpc_reachable=False,
        profiles_count=1 if profiles_file_exists else 0,
        warnings=warnings,
    )

    _render_doctor_report(report, profiles_file_exists=profiles_file_exists)
    return 0


def _render_doctor_report(report: DoctorReport, profiles_file_exists: bool) -> None:
    console.print(f"[bold]bimarz version:[/bold] {report.bimarz_version}")
    console.print(f"[bold]environment:[/bold] {report.environment.value}")

    if report.xray_binary_found:
        console.print(f"[bold]xray-core binary:[/bold] [green]found[/green] ({report.xray_binary_path})")
        console.print(f"[bold]xray-core version:[/bold] {report.xray_version or 'unknown'}")
    else:
        console.print("[bold]xray-core binary:[/bold] [red]not found[/red]")

    console.print(f"[bold]gRPC control API:[/bold] {'reachable' if report.grpc_reachable else 'not checked yet'}")
    profile_status = "exists (run 'bimarz profile list' for details)" if profiles_file_exists else "none yet"
    console.print(f"[bold]profile store:[/bold] {profile_status} (file: {PROFILES_FILE})")

    for warning in report.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")


def _run_profile_add(args: argparse.Namespace) -> int:
    """Implements `bimarz profile add <vless-link>`.

    پیاده‌سازی `bimarz profile add <vless-link>`.
    """
    try:
        vless = parse_vless_link(args.link)
    except SubscriptionParseError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1

    profile_id = str(uuid.uuid4())
    profile = ServerProfile(
        profile_id=profile_id,
        tag=profile_id[:8],
        remark=vless.remark,
        outbound_config=asdict(vless),
        added_at_iso=datetime.now(timezone.utc).isoformat(),
    )

    try:
        store = ProfileStore()
        store.add_profile(profile)
    except ProfileStoreError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1

    console.print(f"[green]added[/green] profile '{profile.remark}' (id: {profile.profile_id})")
    return 0


def _run_profile_list(args: argparse.Namespace) -> int:
    """Implements `bimarz profile list`.

    پیاده‌سازی `bimarz profile list`.
    """
    try:
        store = ProfileStore()
        profiles = store.list_profiles()
    except ProfileStoreError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1

    if not profiles:
        console.print("no profiles saved yet. Add one with: bimarz profile add <vless-link>")
        return 0

    for profile in profiles:
        outbound = profile.outbound_config
        address = outbound.get("address", "?")
        port = outbound.get("port", "?")
        console.print(f"[bold]{profile.profile_id}[/bold]  {profile.remark}  ({address}:{port})")
    return 0


def _run_profile_remove(args: argparse.Namespace) -> int:
    """Implements `bimarz profile remove <profile-id>`.

    پیاده‌سازی `bimarz profile remove <profile-id>`.
    """
    try:
        store = ProfileStore()
        store.remove_profile(args.profile_id)
    except ProfileStoreError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1

    console.print(f"[green]removed[/green] profile '{args.profile_id}'")
    return 0


async def _connect_with_retry(engine_client_class):
    """Retries connecting to xray-core's gRPC API a few times, since the
    process needs a moment to come up after being started.

    اتصال به gRPC API خود xray-core را چند بار دوباره امتحان می‌کند، چون
    پروسه بعد از اجرا شدن به یک لحظه زمان نیاز دارد تا بالا بیاید.
    """
    last_error: Exception | None = None
    for _ in range(GRPC_CONNECT_RETRY_ATTEMPTS):
        try:
            return await engine_client_class.connect(DEFAULT_GRPC_ENDPOINT)
        except Exception as exc:  # noqa: BLE001 — retried broadly, re-raised as-is at the end
            last_error = exc
            await asyncio.sleep(GRPC_CONNECT_RETRY_DELAY_SECONDS)
    raise XrayManagerError(f"xray-core's gRPC API did not come up in time: {last_error}")


async def _connect_async(profile: ServerProfile, binary_path) -> int:
    """The actual async orchestration behind `bimarz connect`: writes a
    runtime config, starts xray-core, adds the real outbound via gRPC,
    then waits until interrupted, cleaning up either way.

    هسته‌ی async پشت `bimarz connect`: یک کانفیگ runtime می‌نویسد،
    xray-core را اجرا می‌کند، outbound واقعی را از طریق gRPC اضافه می‌کند،
    سپس تا زمان قطع‌شدن منتظر می‌ماند و در هر صورت تمیزکاری می‌کند.
    """
    engine_client_class = get_engine_client_class()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CONFIG_DIR / "connect-runtime.json"
    config_path.write_text(build_connect_config(), encoding="utf-8")

    xray_process = XrayProcess(binary_path=binary_path, config_path=config_path)
    try:
        xray_process.start()
    except XrayManagerError as exc:
        console.print(f"[red]error:[/red] could not start xray-core: {exc}")
        return 1

    client = None
    exit_code = 0
    try:
        client = await _connect_with_retry(engine_client_class)

        outbound = profile.outbound_config
        await client.add_vless_reality_outbound(
            tag=profile.tag,
            uuid=outbound["uuid"],
            flow=outbound["flow"],
            address=outbound["address"],
            port=outbound["port"],
            network=outbound["network"],
            sni=outbound["sni"],
            fingerprint=outbound["fingerprint"],
            public_key_b64=outbound["public_key"],
            short_id_hex=outbound["short_id"],
            spider_x=outbound["spider_x"],
        )

        console.print(f"[green]connected[/green] using profile '{profile.remark}'")
        console.print(f"local SOCKS proxy: 127.0.0.1:{DEFAULT_LOCAL_SOCKS_PORT}")
        console.print("press Ctrl+C to disconnect")

        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        # با Ctrl+C، اینجا asyncio.CancelledError پرتاب می‌شود، نه
        # KeyboardInterrupt (طبق رفتار asyncio از پایتون ۳.۱۱ به بعد). این
        # را عمداً دوباره پرتاب نمی‌کنیم تا asyncio.run() بدون traceback
        # زشت و تمیز برگردد.
        # On Ctrl+C, asyncio.CancelledError is raised here, not
        # KeyboardInterrupt (per asyncio's behavior since Python 3.11). We
        # deliberately do not re-raise it so asyncio.run() returns cleanly
        # without an ugly traceback.
        console.print("\ndisconnecting...")
    except Exception as exc:  # noqa: BLE001 — reported to the user, then cleaned up below
        console.print(f"[red]error:[/red] {exc}")
        exit_code = 1
    finally:
        if client is not None:
            try:
                await client.remove_outbound(profile.tag)
            except Exception:  # noqa: BLE001 — best-effort cleanup, never masks the real error
                pass
        xray_process.stop()

    return exit_code


def _run_connect(args: argparse.Namespace) -> int:
    """Implements `bimarz connect <profile-id>`.

    پیاده‌سازی `bimarz connect <profile-id>`.
    """
    try:
        store = ProfileStore()
        profile = store.get_profile(args.profile_id)
    except ProfileStoreError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1

    binary_path = find_xray_binary(explicit_path=args.xray_bin)
    if binary_path is None:
        console.print(
            "[red]error:[/red] xray-core binary not found. Install it and "
            "either add it to PATH or pass --xray-bin explicitly."
        )
        return 1

    try:
        return asyncio.run(_connect_async(profile, binary_path))
    except EngineNotBuiltError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 1
    except KeyboardInterrupt:
        # فرار اضطراری: اگه Ctrl+C دوباره (یا در زمانی نادر) به‌جای
        # CancelledError به‌صورت KeyboardInterrupt واقعی برسه، همینجا هم
        # تمیز خارج می‌شویم.
        # Safety net: if Ctrl+C ever arrives as a real KeyboardInterrupt
        # instead of CancelledError (a double Ctrl+C or another edge
        # case), we still exit cleanly here.
        console.print("\ndisconnected")
        return 0
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bimarz", description="Cross-platform xray-core orchestrator")
    parser.add_argument("--debug", action="store_true", help="enable verbose error output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="diagnose the local environment and xray-core setup")
    doctor_parser.add_argument(
        "--xray-bin",
        default=None,
        help=f"explicit path to the xray-core binary (default: search PATH for '{DEFAULT_XRAY_BINARY}')",
    )
    doctor_parser.set_defaults(handler=_run_doctor)

    profile_parser = subparsers.add_parser("profile", help="manage server profiles")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_action", required=True)

    add_parser = profile_subparsers.add_parser("add", help="add a profile from a vless:// share link")
    add_parser.add_argument("link", help="a vless:// share link (VLESS + Reality + Vision only)")
    add_parser.set_defaults(handler=_run_profile_add)

    list_parser = profile_subparsers.add_parser("list", help="list saved profiles")
    list_parser.set_defaults(handler=_run_profile_list)

    remove_parser = profile_subparsers.add_parser("remove", help="remove a saved profile by id")
    remove_parser.add_argument("profile_id", help="the profile id shown by 'bimarz profile list'")
    remove_parser.set_defaults(handler=_run_profile_remove)

    connect_parser = subparsers.add_parser("connect", help="start xray-core and connect using a saved profile")
    connect_parser.add_argument("profile_id", help="the profile id shown by 'bimarz profile list'")
    connect_parser.add_argument(
        "--xray-bin",
        default=None,
        help=f"explicit path to the xray-core binary (default: search PATH for '{DEFAULT_XRAY_BINARY}')",
    )
    connect_parser.set_defaults(handler=_run_connect)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        exit_code = args.handler(args)
    except BinaryNotFoundError as exc:
        console.print(f"[red]error:[/red] {exc}")
        exit_code = 1
    except XrayManagerError as exc:
        console.print(f"[red]error:[/red] {exc}")
        if args.debug:
            console.print_exception()
        exit_code = 1
    except Exception as exc:  # noqa: BLE001 — intentional last-resort boundary catch
        console.print(f"[red]unexpected error:[/red] {exc}")
        if args.debug:
            console.print_exception()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
