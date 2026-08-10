#!/usr/bin/env python3
"""
CLI entry-point for bimarz.
نقطه ورود CLI برای bimarz.
"""

from __future__ import annotations

import argparse
import logging
from typing import NoReturn

from rich.console import Console

from bimarz.commands.connect import run_connect
from bimarz.commands.doctor import run_doctor
from bimarz.commands.healthcheck import run_healthcheck
from bimarz.commands.killswitch import (
    run_killswitch_disable,
    run_killswitch_enable,
    run_killswitch_status,
)
from bimarz.commands.profile import (
    run_profile_add,
    run_profile_list,
    run_profile_remove,
)
from bimarz.config import AppConfig
from bimarz.constants import BIMARZ_VERSION

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    """Build and configure the complete command-line parser.

    ساخت و پیکربندی کامل parser خط فرمان.
    """
    parser = argparse.ArgumentParser(
        prog="bimarz",
        description="Professional management layer for xray-core.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {BIMARZ_VERSION}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show full technical traceback and enable DEBUG logging.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run a full environment check.",
    )
    doctor_parser.add_argument(
        "--xray-bin",
        type=str,
        default=None,
        help="Path to the xray-core binary.",
    )
    doctor_parser.add_argument(
        "--doctor-timeout",
        type=float,
        default=None,
        help="Override the doctor gRPC timeout in seconds.",
    )
    doctor_parser.set_defaults(func=run_doctor)

    profile_parser = subparsers.add_parser(
        "profile",
        help="Manage server profiles.",
    )
    profile_sub = profile_parser.add_subparsers(
        dest="profile_command",
        required=True,
    )

    profile_add = profile_sub.add_parser(
        "add",
        help="Add a profile from a VLESS share link.",
    )
    profile_add.add_argument(
        "link",
        type=str,
        help="VLESS share link.",
    )
    profile_add.set_defaults(func=run_profile_add)

    profile_list = profile_sub.add_parser(
        "list",
        help="List saved profiles.",
    )
    profile_list.set_defaults(func=run_profile_list)

    profile_remove = profile_sub.add_parser(
        "remove",
        help="Remove a profile by ID.",
    )
    profile_remove.add_argument(
        "profile_id",
        type=str,
        help="Profile identifier.",
    )
    profile_remove.set_defaults(func=run_profile_remove)

    healthcheck = subparsers.add_parser(
        "healthcheck",
        help="Check all profiles in parallel.",
    )
    healthcheck.set_defaults(func=run_healthcheck)

    connect = subparsers.add_parser(
        "connect",
        help="Connect using a saved profile.",
    )
    connect.add_argument(
        "profile_id",
        type=str,
        help="Profile identifier.",
    )
    connect.add_argument(
        "--auto-failover",
        action="store_true",
        help="Enable automatic failover on connection failure.",
    )
    connect.add_argument(
        "--killswitch",
        action="store_true",
        help="Enable the kill-switch for the connection.",
    )
    connect.set_defaults(func=run_connect)

    killswitch = subparsers.add_parser(
        "killswitch",
        help="Manage the kill-switch independently.",
    )
    killswitch_sub = killswitch.add_subparsers(
        dest="ks_command",
        required=True,
    )

    killswitch_enable = killswitch_sub.add_parser(
        "enable",
        help="Enable the kill-switch.",
    )
    killswitch_enable.add_argument(
        "--interface",
        type=str,
        default="tun0",
        help="Network interface protected by the kill-switch.",
    )
    killswitch_enable.add_argument(
        "--xray-uid",
        type=int,
        default=None,
        help="UID used by xray-core.",
    )
    killswitch_enable.set_defaults(func=run_killswitch_enable)

    killswitch_disable = killswitch_sub.add_parser(
        "disable",
        help="Disable the kill-switch.",
    )
    killswitch_disable.set_defaults(func=run_killswitch_disable)

    killswitch_status = killswitch_sub.add_parser(
        "status",
        help="Show the current kill-switch status.",
    )
    killswitch_status.set_defaults(func=run_killswitch_status)

    return parser


def main() -> NoReturn:
    """Run the BiMarz command-line interface.

    اجرای رابط خط فرمان BiMarz.
    """
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
        console.print(
            "[yellow]hint:[/yellow] run with --debug for full traceback, or 'bimarz doctor' to check your setup"
        )
        raise SystemExit(1) from exc

    raise SystemExit(0)


if __name__ == "__main__":
    main()
