"""
`bimarz profile add/list/remove` command handlers.
هندلرهای دستور `bimarz profile add/list/remove`.
"""

from __future__ import annotations

import argparse

from rich.console import Console

from bimarz.config import AppConfig
from bimarz.helpers import format_profile_address
from bimarz.services.profile import ProfileService

console = Console()


def run_profile_add(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    try:
        profile = svc.add_from_link(args.link)
        console.print(f"[green]✓[/green] Profile added: {profile.profile_id} ({format_profile_address(profile)})")
    except ValueError as exc:
        console.print(f"[red]Invalid link: {exc}[/red]")
        raise SystemExit(1) from exc
    except Exception as exc:
        console.print(f"[red]Failed to add profile: {exc}[/red]")
        raise SystemExit(1) from exc


def run_profile_list(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    profiles = svc.list_profiles()
    if not profiles:
        console.print("[dim]No profiles saved.[/dim]")
        return
    for profile in profiles:
        addr = format_profile_address(profile)
        name = getattr(profile, "name", "") or ""
        extra = f" ({name})" if name else ""
        console.print(f"{profile.profile_id}: {addr}{extra}")


def run_profile_remove(args: argparse.Namespace, config: AppConfig) -> None:
    svc = ProfileService()
    try:
        svc.remove(args.profile_id)
        console.print(f"[green]Removed profile {args.profile_id}[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to remove profile: {exc}[/red]")
        raise SystemExit(1) from exc
