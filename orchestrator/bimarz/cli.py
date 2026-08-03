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
from bimarz.commands.profile import run_profile_add, run_profile_list, run_profile_remove
from bimarz.config import AppConfig
from bimarz.constants import BIMARZ_VERSION

console = Console()


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
    doctor_parser.set_defaults(func=run_doctor)

    profile_parser = subparsers.add_parser("profile", help="Manage server profiles.")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

    p_add = profile_sub.add_parser("add", help="Add a profile from a VLESS share link.")
    p_add.add_argument("link", type=str)
    p_add.set_defaults(func=run_profile_add)

    p_list = profile_sub.add_parser("list", help="List saved profiles.")
    p_list.set_defaults(func=run_profile_list)

    p_remove = profile_sub.add_parser("remove", help="Remove a profile by ID.")
    p_remove.add_argument("profile_id", type=str)
    p_remove.set_defaults(func=run_profile_remove)

    hc = subparsers.add_parser("healthcheck", help="Check all profiles in parallel.")
    hc.set_defaults(func=run_healthcheck)

    conn = subparsers.add_parser("connect", help="Connect using a profile.")
    conn.add_argument("profile_id", type=str)
    conn.add_argument("--auto-failover", action="store_true")
    conn.add_argument("--killswitch", action="store_true")
    conn.set_defaults(func=run_connect)

    ks = subparsers.add_parser("killswitch", help="Manage kill-switch independently.")
    ks_sub = ks.add_subparsers(dest="ks_command", required=True)

    ks_en = ks_sub.add_parser("enable", help="Enable kill-switch.")
    ks_en.add_argument("--interface", type=str, default="tun0")
    ks_en.add_argument("--xray-uid", type=int, default=None)
    ks_en.set_defaults(func=run_killswitch_enable)

    ks_dis = ks_sub.add_parser("disable", help="Disable kill-switch.")
    ks_dis.set_defaults(func=run_killswitch_disable)

    ks_st = ks_sub.add_parser("status", help="Show kill-switch status.")
    ks_st.set_defaults(func=run_killswitch_status)

    return parser


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
        console.print(
            "[yellow]hint:[/yellow] run with --debug for full traceback, "
            "or 'bimarz doctor' to check your setup"
        )
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
