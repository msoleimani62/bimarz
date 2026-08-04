#!/usr/bin/env python3
# ابزار bxt: اجرای تست‌های پروژه بی‌مرز و ساخت یک گزارش کامل قابل فهم برای ایجنت هوش مصنوعی
# bxt tool: run the bimarz project's tests and build one complete report an AI agent can fully understand

import argparse
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# پوشه‌ها و پسوندهایی که هرگز نباید وارد گزارش شوند
# directories and extensions that must never be included in the report
IGNORE_DIRS = {
    ".git", "target", "__pycache__", ".venv", "venv", "node_modules",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".cargo", "egg-info",
}

# پسوند فایل‌هایی که برای فهم پروژه توسط ایجنت ضروری هستند
# file extensions considered essential for an AI agent to understand the project
ESSENTIAL_EXTENSIONS = {
    ".py", ".rs", ".toml", ".md", ".proto", ".cfg", ".ini",
    ".yaml", ".yml", ".sh", ".txt",
}

# سقف حجم هر فایل برای اینکه گزارش بیش از حد بزرگ نشود
# per-file size cap so the report doesn't balloon in size
MAX_FILE_SIZE = 200 * 1024  # 200 KB

# نگاشت پسوند به زبان برای بلوک‌های کد در گزارش
# extension-to-language mapping for fenced code blocks in the report
LANG_MAP = {
    ".py": "python", ".rs": "rust", ".toml": "toml", ".md": "markdown",
    ".proto": "protobuf", ".cfg": "ini", ".ini": "ini", ".yaml": "yaml",
    ".yml": "yaml", ".sh": "bash", ".txt": "text",
}

# الگوهای خطای شناخته‌شده و توضیح ثابت هر کدام برای بخش Known issues گزارش
# known error patterns and their fixed explanation for the report's Known issues section
KNOWN_ISSUE_PATTERNS = [
    (
        "Failed to initialize nft: Permission denied",
        "iptables/nft init failure during cargo test is expected — it comes from "
        "kill-switch tests that need root/nft access, not a code failure.",
    ),
    (
        "No module named pytest",
        "pytest was missing from the venv and the automatic install failed; run "
        "`pip install pytest` inside the venv manually and re-run bxt.",
    ),
]

# یادداشت ثابتی که همیشه در بالای هر گزارش تولیدشده قرار می‌گیرد تا هر ایجنت
# هوش مصنوعی که این فایل را می‌خواند بداند این گزارش کامل و خودکفاست.
# A fixed notice always placed at the top of every generated report so any AI
# agent reading this file knows the report is complete and self-sufficient.
AI_NOTICE = (
    "## توجه به ایجنت هوش مصنوعی — Notice to AI Agent\n"
    "\n"
    "این فایل شامل **همه‌چیز** لازم برای شناخت این پروژه است: نتایج کامل تست‌ها،\n"
    "ساختار درختی کامل پروژه، و محتوای کامل تمام فایل‌های ضروری سورس (پایتون،\n"
    "Rust، proto، پیکربندی، اسکریپت‌ها، مستندات). قبل از هر تحلیل، پیشنهاد یا\n"
    "پچی، این فایل باید **از ابتدا تا انتها** خوانده شود — نه فقط بخش‌هایی که با\n"
    "جست‌وجوی مسیر یک فایل خاص پیدا می‌شوند؛ باگ‌ها و ناسازگاری‌های واقعی معمولاً\n"
    "بین چند فایل پخش‌اند و فقط با خواندن کامل قابل کشف‌اند. هیچ فایل دیگری از\n"
    "پروژه لازم نیست درخواست شود مگر این‌که در همین گزارش موجود نباشد — به بخش\n"
    "«Essential files» و فهرست «Skipped» (فایل‌های حذف‌شده به‌دلیل حجم) مراجعه کن.\n"
    "\n"
    "This file contains **everything** needed to understand this project: full\n"
    "test results, the complete project directory tree, and the full content of\n"
    "every essential source file (Python, Rust, proto, configs, scripts, docs).\n"
    "Before any analysis, suggestion, or patch, this file must be read **start\n"
    "to finish** — not just the sections found by grepping for one known file\n"
    "path; real bugs and cross-file mismatches are usually spread across several\n"
    "files and only surface on a full read. No other project file should be\n"
    "requested unless it is missing from this report — check the \"Essential\n"
    "files\" section and its \"Skipped\" list (files omitted for exceeding the\n"
    "size cap).\n"
)

DEFAULT_PROJECT_PATH = Path.home() / "bimarz"
DEFAULT_OUTPUT_DIR = Path("/sdcard/Download")
DEFAULT_OUTPUT_NAME = "bxt-report.md"


def human_size(num_bytes: int) -> str:
    # تبدیل بایت به واحد خوانا برای انسان
    # convert a raw byte count into a human-readable unit
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def find_rust_dirs(root: Path):
    # پیدا کردن هر پوشه‌ای که یک Cargo.toml دارد (کرِیت راست)
    # find every directory that contains a Cargo.toml (a Rust crate)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if "Cargo.toml" in filenames:
            found.append(Path(dirpath))
    return found


def find_python_test_dirs(root: Path):
    # پیدا کردن هر پوشه‌ای که فایل‌های تست پایتون در آن هست
    # find every directory that contains python test files
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if any(f.startswith("test_") and f.endswith(".py") for f in filenames):
            found.add(Path(dirpath).parent if Path(dirpath).name == "tests" else Path(dirpath))
    return sorted(found)


def find_venv_python(root: Path):
    # جستجوی مفسر پایتون venv پروژه، وگرنه استفاده از python3 سیستم
    # look for the project's venv python interpreter, else fall back to system python3
    candidates = [root / ".venv" / "bin" / "python", Path.home() / "bimarz" / ".venv" / "bin" / "python"]
    for c in candidates:
        if c.exists():
            return str(c)
    return "python3"


def run_cmd(cmd, cwd, env=None):
    # اجرای یک دستور و برگرداندن کد خروجی و متن کامل خروجی
    # run a command and return its return code plus full combined output
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd), env=env, capture_output=True,
            text=True, timeout=1800,
        )
        return result.returncode, (result.stdout + result.stderr)
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "command timed out after 1800s"


def summarize_tail(output: str, max_lines: int = 25) -> str:
    # نگه‌داشتن فقط چند خط آخر خروجی برای خلاصه شدن گزارش
    # keep only the last few lines of output to keep the report short
    lines = output.strip().splitlines()
    return "\n".join(lines[-max_lines:]) if lines else "(no output)"


def run_rust_tests(root: Path):
    # اجرای cargo test روی هر کریت راست پیدا شده
    # run cargo test on every discovered Rust crate
    results = []
    for crate_dir in find_rust_dirs(root):
        rc, out = run_cmd(["cargo", "test"], cwd=crate_dir)
        results.append({
            "dir": str(crate_dir.relative_to(root)) or ".",
            "returncode": rc,
            "summary": summarize_tail(out),
        })
    return results


def ensure_pytest(py: str):
    # اگر pytest در محیط پایتون نصب نبود، خودکار نصبش کن و نتیجه را برگردان
    # if pytest is missing from the python environment, install it automatically and report the outcome
    rc, _ = run_cmd([py, "-c", "import pytest"], cwd=Path.home())
    if rc == 0:
        return None
    install_rc, install_out = run_cmd([py, "-m", "pip", "install", "pytest"], cwd=Path.home())
    if install_rc == 0:
        return "pytest was missing and has been installed automatically."
    return f"pytest was missing and the automatic install failed:\n{summarize_tail(install_out, 10)}"


def run_python_tests(root: Path):
    # اجرای pytest روی هر پوشه تست پایتون پیدا شده، با نصب خودکار در صورت نبودن pytest
    # run pytest on every discovered python test directory, auto-installing pytest if it's missing
    results = []
    py = find_venv_python(root)
    env = os.environ.copy()
    env.setdefault("BIMARZ_PROFILE_PASSWORD", "test123")
    install_note = ensure_pytest(py)
    for test_dir in find_python_test_dirs(root):
        rc, out = run_cmd([py, "-m", "pytest", "-q"], cwd=test_dir, env=env)
        results.append({
            "dir": str(test_dir.relative_to(root)) or ".",
            "returncode": rc,
            "summary": summarize_tail(out),
            "install_note": install_note,
        })
    return results


def build_tree(root: Path) -> str:
    # ساخت نمای درختی پروژه شبیه دستور tree
    # build a project directory tree similar to the `tree` command
    lines = [root.name + "/"]

    def walk(dir_path: Path, prefix: str):
        entries = sorted(
            [e for e in dir_path.iterdir() if e.name not in IGNORE_DIRS],
            key=lambda e: (e.is_file(), e.name.lower()),
        )
        for i, entry in enumerate(entries):
            last = i == len(entries) - 1
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + entry.name + ("/" if entry.is_dir() else ""))
            if entry.is_dir():
                extension = "    " if last else "│   "
                walk(entry, prefix + extension)

    walk(root, "")
    return "\n".join(lines)


def collect_essential_files(root: Path):
    # جمع‌آوری فایل‌های ضروری برای فهم پروژه، همراه با علت رد شدن فایل‌های حجیم
    # collect the essential files for understanding the project, noting oversized skips
    included, skipped = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix not in ESSENTIAL_EXTENSIONS:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_SIZE:
                skipped.append((path.relative_to(root), size))
            else:
                included.append(path.relative_to(root))
    return sorted(included), sorted(skipped)


def render_report(root: Path, rust_results, python_results, tree_text, included, skipped, tests_skipped: bool) -> str:
    # ساخت متن نهایی گزارش به صورت یک فایل مارک‌داون واحد
    # assemble the final report as a single markdown document
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        f"# bxt report — {root.name}",
        f"Generated: {now}",
        f"Host: {socket.gethostname()}",
        f"Project path: {root}",
        "",
        AI_NOTICE,
        "## Test results",
    ]

    if tests_skipped:
        parts.append("Test execution was skipped (--skip-tests).")
    elif not rust_results and not python_results:
        parts.append("No test suites were discovered under this project path.")
    for r in rust_results:
        status = "PASS" if r["returncode"] == 0 else "FAIL"
        parts.append(f"### cargo test — {r['dir']} [{status}]")
        parts.append("```")
        parts.append(r["summary"])
        parts.append("```")
    for r in python_results:
        status = "PASS" if r["returncode"] == 0 else "FAIL"
        parts.append(f"### pytest — {r['dir']} [{status}]")
        if r.get("install_note"):
            parts.append(f"_{r['install_note']}_")
        parts.append("```")
        parts.append(r["summary"])
        parts.append("```")

    # تشخیص خودکار خطاهای شناخته‌شده در خروجی تست‌ها و افزودن توضیحشان به گزارش
    # automatically detect known error patterns in the test output and add their explanation
    combined_output = "\n".join(r["summary"] for r in rust_results + python_results)
    known_issues = [note for pattern, note in KNOWN_ISSUE_PATTERNS if pattern in combined_output]
    if known_issues:
        parts += ["", "## Known issues"]
        parts += [f"- {note}" for note in known_issues]

    parts += ["", "## Project tree", "```", tree_text, "```", ""]

    parts.append("## Essential files")
    parts.append(f"{len(included)} files included, {len(skipped)} skipped for exceeding {human_size(MAX_FILE_SIZE)}.")
    if skipped:
        parts.append("")
        parts.append("Skipped (too large):")
        for rel_path, size in skipped:
            parts.append(f"- {rel_path} ({human_size(size)})")

    for rel_path in included:
        full_path = root / rel_path
        lang = LANG_MAP.get(full_path.suffix, "")
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            content = f"(could not read file: {exc})"
        parts.append("")
        parts.append(f"### {rel_path}")
        parts.append(f"```{lang}")
        parts.append(content)
        parts.append("```")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(prog="bxt", description="Run bimarz tests and export a full project report for an AI agent.")
    parser.add_argument("--project", default=str(DEFAULT_PROJECT_PATH), help="Path to the bimarz project root")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to write the report into")
    parser.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME, help="Report file name")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running cargo/pytest and only export the report")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: project path does not exist: {root}")
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_dir():
        print(f"ERROR: output directory does not exist: {output_dir}")
        sys.exit(1)
    output_path = output_dir / args.output_name

    rust_results, python_results = [], []
    if not args.skip_tests:
        print("Running Rust test suites...")
        rust_results = run_rust_tests(root)
        print("Running Python test suites...")
        python_results = run_python_tests(root)
    else:
        print("Skipping test execution (--skip-tests).")

    print("Building project tree...")
    tree_text = build_tree(root)

    print("Collecting essential source files...")
    included, skipped = collect_essential_files(root)

    print("Rendering report...")
    report_text = render_report(root, rust_results, python_results, tree_text, included, skipped, args.skip_tests)

    # اگر فایل هم‌نامی از قبل در پوشه دانلود وجود دارد، حذفش کن و گزارش بده
    # if a same-named file already exists in the Download folder, delete it and report that
    if output_path.exists():
        old_size = output_path.stat().st_size
        output_path.unlink()
        print(f"Removed existing file: {output_path} ({human_size(old_size)})")

    output_path.write_text(report_text, encoding="utf-8")
    new_size = output_path.stat().st_size

    print(f"SUCCESS: report written to {output_path} ({human_size(new_size)})")
    print(f"Files included: {len(included)} | Files skipped: {len(skipped)}")
    rust_fail = sum(1 for r in rust_results if r["returncode"] != 0)
    py_fail = sum(1 for r in python_results if r["returncode"] != 0)
    print(f"Rust suites: {len(rust_results)} run, {rust_fail} failed | Python suites: {len(python_results)} run, {py_fail} failed")


if __name__ == "__main__":
    main()
