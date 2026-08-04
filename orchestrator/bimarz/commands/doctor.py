"""
`bimarz doctor` command handler.
هندلر دستور `bimarz doctor`.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from rich.console import Console

from bimarz.config import AppConfig
from bimarz.constants import (
    BIMARZ_VERSION,
    DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR,
    DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS,
)
from bimarz.models import DoctorReport, GrpcStatus
from bimarz.services.doctor import DoctorService

console = Console()


def _render_doctor_report(report: DoctorReport) -> None:
    """Pretty-print the doctor diagnostic report.
    گزارش تشخیصی doctor را به صورت زیبا چاپ می‌کند.
    """
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
        f"[{status_colour}]●[/{status_colour}] gRPC status: {report.grpc_status.value} at {report.grpc_endpoint}"
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


def run_doctor(args: argparse.Namespace, config: AppConfig) -> None:
    asyncio.run(_run_doctor_async(args, config))
