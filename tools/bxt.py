#!/usr/bin/env python3

# فارسی: نقطه ورود ابزار bxt
# English: Entry point for the bxt tool

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_PATH = Path.home() / "bimarz"
DEFAULT_OUTPUT_DIR = Path("/sdcard/Download")
DEFAULT_OUTPUT_NAME = "bxt-report.md"

MAX_TREE_DEPTH = 8
MAX_TREE_ENTRIES = 100
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_ISSUE_ROWS = 500

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "target",
    "build",
    "dist",
    "node_modules",
}

ESSENTIAL_EXTENSIONS = {
    ".py",
    ".rs",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".lock",
    ".sh",
    ".bash",
    ".zsh",
    ".ini",
    ".cfg",
    ".conf",
    ".proto",
}

LANG_MAP = {
    ".py": "python",
    ".rs": "rust",
    ".toml": "toml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".proto": "protobuf",
}

AI_NOTICE = "This report is generated for AI analysis and contains project metadata, test results and source files."

KNOWN_ISSUE_PATTERNS = [
    (
        "Failed to parse",
        "One or more source files contain syntax errors.",
    ),
    (
        "ModuleNotFoundError",
        "A required Python dependency is missing.",
    ),
    (
        "error:",
        "Compilation or lint errors were detected.",
    ),
]


def human_size(size: int) -> str:
    # فارسی: تبدیل اندازه فایل به رشته خوانا
    # English: Convert bytes to human readable string

    units = ["B", "KiB", "MiB", "GiB"]

    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{size} B"


def parse_args() -> argparse.Namespace:
    # فارسی: پردازش آرگومان‌های خط فرمان
    # English: Parse command line arguments

    parser = argparse.ArgumentParser(
        prog="bxt",
        description="Generate a complete AI-ready project report.",
    )

    parser.add_argument(
        "--project",
        default=str(DEFAULT_PROJECT_PATH),
        help="Project root directory",
    )

    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory",
    )

    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help="Output markdown file",
    )

    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests",
    )

    parser.add_argument(
        "--quality",
        action="store_true",
        help="Run quality checks",
    )

    return parser.parse_args()


WARNING_PATTERNS = (
    "warning:",
    "warning[",
    "deprecated",
    "unused",
)

ERROR_PATTERNS = (
    "error:",
    "failed",
    "traceback",
    "panic",
    "exception",
)


def run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: int = 300,
) -> tuple[int, str]:
    # فارسی: اجرای یک دستور و دریافت خروجی
    # English: Execute a command and capture its output

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, "Command timed out."
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"

    return completed.returncode, completed.stdout


def summarize_tail(
    output: str,
    lines: int = 80,
) -> str:
    # فارسی: خلاصه خروجی
    # English: Return the last output lines

    data = output.strip().splitlines()

    if len(data) <= lines:
        return output.strip()

    return "\n".join(data[-lines:])


def scan_for_issues(
    source: str,
    output: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    # فارسی: استخراج هشدارها و خطاها
    # English: Extract warnings and errors

    warnings: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []

    for line in output.splitlines():
        lower = line.lower()

        if any(pattern in lower for pattern in WARNING_PATTERNS):
            warnings.append((source, line.strip()))

        if any(pattern in lower for pattern in ERROR_PATTERNS):
            errors.append((source, line.strip()))

    return warnings, errors


def git(
    root: Path,
    *args: str,
) -> str:
    # فارسی: اجرای دستورات Git
    # English: Execute Git commands

    rc, output = run_cmd(
        ["git", *args],
        cwd=root,
        timeout=60,
    )

    if rc == 0:
        return output.strip()

    return "(unavailable)"


def collect_git_snapshot(
    root: Path,
) -> dict[str, str]:
    # فارسی: جمع‌آوری وضعیت Git
    # English: Collect Git snapshot

    return {
        "branch": git(
            root,
            "branch",
            "--show-current",
        ),
        "commit": git(
            root,
            "rev-parse",
            "--short",
            "HEAD",
        ),
        "status": git(
            root,
            "status",
            "--short",
        ),
        "log": git(
            root,
            "log",
            "--oneline",
            "-20",
        ),
        "diff": git(
            root,
            "diff",
            "--stat",
        ),
    }


def collect_environment_info() -> dict[str, str]:
    # فارسی: اطلاعات محیط
    # English: Collect environment information

    def version(
        command: list[str],
    ) -> str:
        rc, out = run_cmd(
            command,
            cwd=Path.home(),
            timeout=30,
        )

        if rc == 0:
            return out.strip()

        return "(unavailable)"

    return {
        "python": version([sys.executable, "--version"]),
        "rustc": version(["rustc", "--version"]),
        "cargo": version(["cargo", "--version"]),
        "git": version(["git", "--version"]),
        "ruff": version(["ruff", "--version"]),
    }


def build_tree(root: Path) -> str:
    # فارسی: ساخت درخت پروژه
    # English: Build project tree

    lines: list[str] = [f"{root.name}/"]

    def walk(
        directory: Path,
        prefix: str,
        depth: int,
    ) -> None:
        # فارسی: پیمایش بازگشتی
        # English: Recursive directory walk

        if depth >= MAX_TREE_DEPTH:
            return

        try:
            entries = sorted(
                (item for item in directory.iterdir() if item.name not in IGNORE_DIRS),
                key=lambda item: (
                    item.is_file(),
                    item.name.lower(),
                ),
            )
        except OSError:
            return

        hidden = max(
            0,
            len(entries) - MAX_TREE_ENTRIES,
        )

        entries = entries[:MAX_TREE_ENTRIES]

        for index, entry in enumerate(entries):
            last = index == len(entries) - 1 and hidden == 0

            connector = "└── " if last else "├── "

            lines.append(prefix + connector + entry.name + ("/" if entry.is_dir() else ""))

            if entry.is_dir():
                walk(
                    entry,
                    prefix + ("    " if last else "│   "),
                    depth + 1,
                )

        if hidden:
            lines.append(f"{prefix}└── ... ({hidden} more entries hidden)")

    walk(
        root,
        "",
        0,
    )

    return "\n".join(lines)


def collect_essential_files(
    root: Path,
) -> tuple[list[Path], list[tuple[Path, int]]]:
    # فارسی: جمع‌آوری فایل‌های ضروری
    # English: Collect essential source files

    included: list[Path] = []
    skipped: list[tuple[Path, int]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIRS]

        for filename in filenames:
            path = Path(dirpath) / filename

            if path.suffix.lower() not in ESSENTIAL_EXTENSIONS:
                continue

            try:
                size = path.stat().st_size
            except OSError:
                continue

            rel = path.relative_to(root)

            if size > MAX_FILE_SIZE:
                skipped.append(
                    (
                        rel,
                        size,
                    )
                )
            else:
                included.append(rel)

    included.sort()
    skipped.sort()

    return included, skipped


def run_rust_tests(
    root: Path,
) -> list[dict[str, Any]]:
    # فارسی: اجرای تست‌های Rust
    # English: Execute Rust tests

    results: list[dict[str, Any]] = []

    if not (root / "Cargo.toml").exists():
        return results

    rc, output = run_cmd(
        [
            "cargo",
            "test",
            "--all",
        ],
        cwd=root,
        timeout=3600,
    )

    warnings, errors = scan_for_issues(
        "cargo test",
        output,
    )

    results.append(
        {
            "kind": "cargo test",
            "dir": ".",
            "returncode": rc,
            "summary": summarize_tail(output),
            "raw_output": output,
            "warnings": warnings,
            "errors": errors,
        }
    )

    return results


def run_python_tests(
    root: Path,
) -> list[dict[str, Any]]:
    # فارسی: اجرای تست‌های Python
    # English: Execute Python tests

    results: list[dict[str, Any]] = []

    if shutil.which("pytest") is None:
        return results

    rc, output = run_cmd(
        [
            "pytest",
            "-q",
        ],
        cwd=root,
        timeout=3600,
    )

    warnings, errors = scan_for_issues(
        "pytest",
        output,
    )

    results.append(
        {
            "kind": "pytest",
            "dir": ".",
            "returncode": rc,
            "summary": summarize_tail(output),
            "raw_output": output,
            "warnings": warnings,
            "errors": errors,
        }
    )

    return results


def run_quality_checks(
    root: Path,
) -> list[dict[str, Any]]:
    # فارسی: اجرای بررسی‌های کیفیت کد
    # English: Run quality checks

    results: list[dict[str, Any]] = []

    checks: list[tuple[str, list[str]]] = []

    if shutil.which("ruff"):
        checks.append(
            (
                "ruff check",
                [
                    "ruff",
                    "check",
                    ".",
                    "--output-format=concise",
                ],
            )
        )

    if shutil.which("ruff"):
        checks.append(
            (
                "ruff format",
                [
                    "ruff",
                    "format",
                    ".",
                    "--check",
                ],
            )
        )

    if shutil.which("cargo") and (root / "Cargo.toml").exists():
        checks.append(
            (
                "cargo fmt",
                [
                    "cargo",
                    "fmt",
                    "--all",
                    "--check",
                ],
            )
        )

    if shutil.which("cargo") and (root / "Cargo.toml").exists():
        checks.append(
            (
                "cargo clippy",
                [
                    "cargo",
                    "clippy",
                    "--all-targets",
                    "--all-features",
                    "--",
                    "-D",
                    "warnings",
                ],
            )
        )

    for name, command in checks:
        rc, output = run_cmd(
            command,
            cwd=root,
            timeout=3600,
        )

        warnings, errors = scan_for_issues(
            name,
            output,
        )

        results.append(
            {
                "kind": name,
                "dir": ".",
                "returncode": rc,
                "summary": summarize_tail(output),
                "raw_output": output,
                "warnings": warnings,
                "errors": errors,
            }
        )

    return results


def render_issue_index(
    title: str,
    issues: list[tuple[str, str]],
) -> list[str]:
    # فارسی: ساخت بخش هشدارها و خطاها
    # English: Build warning/error section

    if not issues:
        return [
            f"## {title}",
            "",
            "None detected.",
            "",
        ]

    lines = [
        f"## {title}",
        "",
    ]

    for source, text in issues[:MAX_ISSUE_ROWS]:
        lines.append(f"- **{source}**: `{text}`")

    if len(issues) > MAX_ISSUE_ROWS:
        lines.append(f"- ... ({len(issues) - MAX_ISSUE_ROWS} more)")

    lines.append("")

    return lines


def render_test_output(
    parts: list[str],
    result: dict[str, Any],
) -> None:
    # فارسی: افزودن نتیجه تست به گزارش
    # English: Append test result

    status = "PASS" if result["returncode"] == 0 else "FAIL"

    parts.append(f"### {result['kind']} [{status}]")

    parts.append("```text")
    parts.append(result["summary"])
    parts.append("```")

    if result["returncode"] != 0 and result["raw_output"]:
        parts.extend(
            [
                "",
                "#### Full output",
                "",
                "```text",
                result["raw_output"],
                "```",
                "",
            ]
        )


def render_report(
    root: Path,
    rust_results: list[dict[str, Any]],
    python_results: list[dict[str, Any]],
    quality_results: list[dict[str, Any]],
    git_info: dict[str, str],
    env_info: dict[str, str],
    tree_text: str,
    included: list[Path],
    skipped: list[tuple[Path, int]],
    tests_skipped: bool,
) -> str:
    # فارسی: تولید گزارش نهایی
    # English: Build the final report

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    parts: list[str] = [
        f"# bxt report — {root.name}",
        "",
        f"Generated: {now}",
        f"Host: {socket.gethostname()}",
        f"Project: {root}",
        "",
        AI_NOTICE,
        "",
        "## Environment",
        "",
    ]

    for key, value in env_info.items():
        parts.append(f"- **{key}:** {value}")

    parts.extend(
        [
            "",
            "## Git",
            "",
            f"- Branch: {git_info['branch']}",
            f"- Commit: {git_info['commit']}",
            "",
            "### Status",
            "```text",
            git_info["status"] or "(clean)",
            "```",
            "",
            "### Diff",
            "```text",
            git_info["diff"] or "(none)",
            "```",
            "",
            "### Recent commits",
            "```text",
            git_info["log"],
            "```",
            "",
            "## Test results",
            "",
        ]
    )

    all_warnings: list[tuple[str, str]] = []
    all_errors: list[tuple[str, str]] = []

    if tests_skipped:
        parts.append("Tests skipped.")
        parts.append("")

    for result in rust_results + python_results:
        render_test_output(
            parts,
            result,
        )

        all_warnings.extend(result["warnings"])

        all_errors.extend(result["errors"])

    if quality_results:
        parts.extend(
            [
                "",
                "## Quality checks",
                "",
            ]
        )

        for result in quality_results:
            render_test_output(
                parts,
                result,
            )

            all_warnings.extend(result["warnings"])

            all_errors.extend(result["errors"])

    combined = "\n".join(item["raw_output"] for item in (rust_results + python_results + quality_results))

    detected: list[str] = []

    for pattern, note in KNOWN_ISSUE_PATTERNS:
        if pattern.lower() in combined.lower():
            detected.append(note)

    if detected:
        parts.extend(
            [
                "",
                "## Known issues",
                "",
            ]
        )

        for item in detected:
            parts.append(f"- {item}")

        parts.append("")

    parts.extend(
        render_issue_index(
            "Warnings detected",
            all_warnings,
        )
    )

    parts.extend(
        render_issue_index(
            "Errors detected",
            all_errors,
        )
    )

    parts.extend(
        [
            "## Project tree",
            "",
            "```text",
            tree_text,
            "```",
            "",
            "## Included files",
            "",
            f"{len(included)} included / {len(skipped)} skipped",
            "",
        ]
    )

    if skipped:
        parts.extend(
            [
                "### Skipped files",
                "",
            ]
        )

        for path, size in skipped:
            parts.append(f"- {path} ({human_size(size)})")

        parts.append("")

    for rel in included:
        full = root / rel

        try:
            text = full.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            text = str(exc)

        lang = LANG_MAP.get(
            full.suffix.lower(),
            "",
        )

        parts.extend(
            [
                "",
                f"# FILE: {rel}",
                "",
                f"Size: {human_size(full.stat().st_size)}",
                "",
                f"```{lang}",
                text,
                "```",
            ]
        )

    return "\n".join(parts)


def write_sha256(
    path: Path,
) -> str:
    # فارسی: تولید فایل SHA256
    # English: Generate SHA256 checksum file

    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    checksum_path = path.with_suffix(path.suffix + ".sha256")

    checksum_path.write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    return digest


def main() -> int:
    # فارسی: تابع اصلی برنامه
    # English: Main program entry point

    args = parse_args()

    root = Path(args.project).expanduser().resolve()

    if not root.is_dir():
        print(
            f"Project not found: {root}",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / args.output_name

    print("Collecting Git information...")
    git_info = collect_git_snapshot(root)

    print("Collecting environment information...")
    env_info = collect_environment_info()

    print("Building project tree...")
    tree_text = build_tree(root)

    print("Collecting project files...")
    included, skipped = collect_essential_files(root)

    rust_results: list[dict[str, Any]] = []
    python_results: list[dict[str, Any]] = []
    quality_results: list[dict[str, Any]] = []

    if not args.skip_tests:
        print("Running Rust tests...")
        rust_results = run_rust_tests(root)

        print("Running Python tests...")
        python_results = run_python_tests(root)

    if args.quality:
        print("Running quality checks...")
        quality_results = run_quality_checks(root)

    print("Rendering report...")

    report = render_report(
        root=root,
        rust_results=rust_results,
        python_results=python_results,
        quality_results=quality_results,
        git_info=git_info,
        env_info=env_info,
        tree_text=tree_text,
        included=included,
        skipped=skipped,
        tests_skipped=args.skip_tests,
    )

    output_path.write_text(
        report,
        encoding="utf-8",
    )

    digest = write_sha256(
        output_path,
    )

    print()
    print("=" * 60)
    print("Report completed")
    print("=" * 60)
    print(f"Output : {output_path}")
    print(f"SHA256 : {digest}")
    print(f"Files   : {len(included)}")
    print(f"Skipped : {len(skipped)}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
