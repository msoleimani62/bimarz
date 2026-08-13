# Installation Guide / راهنمای نصب

> ⚠️ **Current status:** BiMarz is distributed **only from source** at this stage. Pre-built wheels are available via GitHub Releases for `x86_64` and `aarch64`, but PyPI publication is deferred until the CI matrix is fully stable.
> ⚠️ **وضعیت فعلی:** بی‌مرز در حال حاضر **فقط از سورس** توزیع می‌شود. wheel های از قبل ساخته‌شده برای `x86_64` و `aarch64` از طریق GitHub Releases در دسترس هستند، ولی انتشار PyPI به تعویق افتاده تا ماتریس CI کاملاً پایدار شود.

---

## Table of Contents / فهرست مطالب

- [Prerequisites / پیش‌نیازها](#prerequisites--پیشنیازها)
- [Quick Start / شروع سریع](#quick-start--شروع-سریع)
- [Step-by-Step / گام‌به‌گام](#step-by-step--گامبهگام)
- [Platform Notes / نکات پلتفرم](#platform-notes--نکات-پلتفرم)
- [Troubleshooting / رفع مشکل](#troubleshooting--رفع-مشکل)
- [Uninstall / حذف نصب](#uninstall--حذف-نصب)

---

## Prerequisites / پیش‌نیازها

| Tool / ابزار | Min version / حداقل نسخه | How to check / چطور چک کنی |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Rust | 1.83+ | `rustc --version` |
| Git | any | `git --version` |
| xray-core binary | 1.8.24 | `xray version` |

### Installing prerequisites / نصب پیش‌نیازها

**Arch Linux / Kali NetHunter (proot):**

```bash
sudo pacman -S python python-virtualenv rust git
# or on Kali:
sudo apt update && sudo apt install python3 python3-venv rustc cargo git
```

**Termux (no root):**

```bash
pkg update
pkg install python rust git
```

**xray-core binary:** Download the matching release from [XTLS/xray-core](https://github.com/XTLS/xray-core/releases) and place it in `~/bin/xray` or any directory in your `$PATH`.

---

## Quick Start / شروع سریع

If you already have all prerequisites:

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip maturin
./scripts/build-release.sh
bimarz doctor
```

---

## Step-by-Step / گام‌به‌گام

### Step 1 — Clone the repository / گام ۱ — کلون کردن ریپازیتوری

```bash
cd ~
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
```

### Step 2 — Fetch official proto files / گام ۲ — واکشی فایل‌های proto رسمی

These are **not** committed to the repo (they must match your exact xray-core binary version).

```bash
XRAY_TAG="v1.8.24"
git clone --depth 1 --branch "$XRAY_TAG"     https://github.com/XTLS/xray-core.git /tmp/xray-core-src
mkdir -p engine-core/proto
cp -r /tmp/xray-core-src/app engine-core/proto/
cp -r /tmp/xray-core-src/common engine-core/proto/
rm -rf /tmp/xray-core-src
```

### Step 3 — Create virtual environment / گام ۳ — ساخت محیط مجازی

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **Tip / نکته:** Always activate the venv before running any `bimarz` command or `maturin` build.
> **نکته:** همیشه قبل از اجرای هر دستور `bimarz` یا build با `maturin`، venv را فعال کن.

### Step 4 — Install build dependencies / گام ۴ — نصب وابستگی‌های build

```bash
pip install --upgrade pip maturin
```

### Step 5 — Build the Rust extension / گام ۵ — ساخت اکستنشن Rust

```bash
maturin develop --release
```

This compiles `engine-core` and installs the Python package in editable mode.

### Step 6 — Verify installation / گام ۶ — بررسی نصب

```bash
bimarz doctor
```

Expected output / خروجی مورد انتظار:

```
bimarz doctor — version 0.2.0
✓ xray-core binary found: <PATH-resolved xray binary> (version: Xray 1.8.24)
● gRPC status: responding at 127.0.0.1:10085
✓ gRPC API is fully responsive
Profiles stored: 0
○ Kill-switch is inactive
```

If you see `gRPC status: listening` instead of `responding`, the Rust extension built successfully but xray-core is not running — this is normal before your first connection.

---

## Platform Notes / نکات پلتفرم

### Arch Linux (desktop)

- Full kernel-level kill-switch available with root access.
- Build with `CARGO_BUILD_JOBS=1` on low-RAM systems (e.g., Dell Inspiron 1525 with 2GB RAM).

### Kali NetHunter inside Termux (proot/chroot)

- Detected automatically via Android kernel mount signals.
- Kernel-level kill-switch is **not possible** without host root — the software fallback activates automatically.
- If `iptables: Failed to initialize nft: Permission denied` appears during tests, this is expected and harmless.

### Plain Termux (no NetHunter)

- Same as Kali NetHunter: software fallback for kill-switch.
- Build may be slower due to limited RAM; use `CARGO_BUILD_JOBS=1`.

### WSL

- Full kernel-level kill-switch available with root access.
- Ensure `xray-core` binary is the Linux build, not Windows.

---

## Troubleshooting / رفع مشکل

### `ImportError: cannot import name '_engine_core'`

The Rust extension is not built. Run:

```bash
source .venv/bin/activate
maturin develop --release
```

### `BinaryNotFoundError: xray-core binary not found`

Install xray-core or specify its path:

```bash
bimarz doctor --xray-bin /path/to/xray
```

### `grpc_status: unreachable` in doctor

xray-core is not running. This is normal before your first `bimarz connect`. The TCP port probe confirms the environment is ready.

### Build fails with "too many leading super keywords"

The proto files were fetched incompletely. Re-run Step 2 and ensure both `app/` and `common/` directories are copied fully.

### Permission denied during `cargo test` (iptables/nft)

Expected on non-root environments. The kill-switch tests require root/nft access. This is not a code failure.

---

## Uninstall / حذف نصب

```bash
source .venv/bin/activate
pip uninstall bimarz
rm -rf ~/.config/bimarz          # user data (profiles, logs)
rm -rf ~/bimarz/.venv            # virtual environment
cd ~ && rm -rf ~/bimarz          # source code (optional)
```

To also remove the xray-core binary (if installed manually):

```bash
rm ~/bin/xray
```

---

*Last updated / آخرین به‌روزرسانی: 2026-08-04*
