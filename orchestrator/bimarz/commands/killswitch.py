"""
`bimarz killswitch enable/disable/status` command handlers.
هندلرهای دستور `bimarz killswitch enable/disable/status`.
"""

from __future__ import annotations

import argparse

from rich.console import Console

from bimarz.config import AppConfig
from bimarz.helpers import get_current_uid
from bimarz.services.killswitch import KillSwitchService

console = Console()


def run_killswitch_enable(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    uid = args.xray_uid if args.xray_uid is not None else get_current_uid()
    svc.enable(interface=args.interface, uid=uid)
    console.print(f"[green]Kill-switch enabled (xray UID: {uid}).[/green]")


def run_killswitch_disable(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    svc.disable()
    console.print("[green]Kill-switch disabled.[/green]")


def run_killswitch_status(args: argparse.Namespace, config: AppConfig) -> None:
    svc = KillSwitchService()
    if svc.is_active():
        console.print("[green]Kill-switch is active[/green]")
    else:
        console.print("[dim]Kill-switch is inactive[/dim]")
