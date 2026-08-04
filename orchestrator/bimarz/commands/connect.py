"""
`bimarz connect` command handler.
هندلر دستور `bimarz connect`.
"""

from __future__ import annotations

import argparse
import asyncio

from rich.console import Console

from bimarz.config import AppConfig
from bimarz.connection import ConnectionService
from bimarz.engine import EngineNotBuiltError
from bimarz.events import ConnectionEvent, EventHandler, EventPayload
from bimarz.models import ServerProfile
from bimarz.services.profile import ProfileService
from bimarz.xray_manager import BinaryNotFoundError

console = Console()


def _make_event_handler() -> EventHandler:
    """Create the default console event handler.
    هندلر پیش‌فرض رویدادهای کنسول را می‌سازد.
    """

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


async def _run_connect_async(args: argparse.Namespace, config: AppConfig) -> None:
    profile_svc = ProfileService()
    profile: ServerProfile | None = profile_svc.get(args.profile_id)
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


def run_connect(args: argparse.Namespace, config: AppConfig) -> None:
    try:
        asyncio.run(_run_connect_async(args, config))
    except BinaryNotFoundError as exc:
        console.print(
            "[red]xray-core binary not found.[/red]\n"
            "[yellow]hint:[/yellow] install xray-core or use --xray-bin /path/to/xray\n"
            "[yellow]hint:[/yellow] run 'bimarz doctor' for full diagnostics"
        )
        raise SystemExit(1) from exc
    except EngineNotBuiltError as exc:
        console.print(
            "[red]Rust extension not built.[/red]\n"
            "[yellow]hint:[/yellow] source .venv/bin/activate && maturin develop --release"
        )
        raise SystemExit(1) from exc
    except Exception as exc:
        if args.debug:
            raise
        console.print(f"[red]Connection failed: {exc}[/red]")
        raise SystemExit(1) from exc
