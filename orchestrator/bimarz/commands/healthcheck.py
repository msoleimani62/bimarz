"""
`bimarz healthcheck` command handler.
هندلر دستور `bimarz healthcheck`.
"""

from __future__ import annotations

import argparse
import asyncio

from rich.console import Console

from bimarz.config import AppConfig
from bimarz.helpers import format_profile_address
from bimarz.services.health import HealthService

console = Console()


async def _run_healthcheck_async(args: argparse.Namespace, config: AppConfig) -> None:
    svc = HealthService()
    results = await svc.check_all()
    if not results:
        console.print("[yellow]No profiles to check.[/yellow]")
        return
    for profile, result in results:
        addr = format_profile_address(profile)
        if isinstance(result, Exception):
            console.print(f"[red]✗[/red] {addr} — error: {result}")
        elif isinstance(result, dict) and result.get("ok"):
            latency = result.get("latency_ms", "?")
            console.print(f"[green]✓[/green] {addr} — {latency}ms")
        else:
            console.print(f"[red]✗[/red] {addr} — unreachable")


def run_healthcheck(args: argparse.Namespace, config: AppConfig) -> None:
    asyncio.run(_run_healthcheck_async(args, config))
