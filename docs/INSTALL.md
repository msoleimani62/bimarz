# Installation Guide / راهنمای نصب

> ⚠️ **Current status:** BiMarz is distributed **from source and as GitHub Releases wheels**. PyPI publication is deferred until the release pipeline is fully stable. Pre-built wheels are published for `x86_64` and `aarch64` (glibc Linux), one per supported CPython version (3.10–3.13) — pick the wheel matching your Python version.
> ⚠️ **وضعیت فعلی:** بی‌مرز **از سورس و به‌صورت wheel در GitHub Releases** توزیع می‌شود. انتشار PyPI به تعویق افتاده تا پایپ‌لاین انتشار کاملاً پایدار شود. wheelهای از پیش ساخته‌شده برای `x86_64` و `aarch64` (لینوکس glibc) منتشر می‌شوند، یکی برای هر نسخه‌ی پشتیبانی‌شده‌ی CPython (۳.۱۰ تا ۳.۱۳) — wheel مطابق با نسخه‌ی پایتونت را انتخاب کن.

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
| Rust | 1.83+ (MSRV declared in `engine-core/Cargo.toml`) | `rustc --version` |
| protoc | any recent | `protoc --version` |
| Git | any | `git --version` |
| xray-core binary | pinned in `engine-core/xray-proto-pin.env` (currently v1.8.24) | `xray version` |

### Installing prerequisites / نصب پیش‌نیازها

**Arch Linux (desktop):**

```bash
sudo pacman -S python python-virtualenv rust protobuf git
```

**Kali / Debian / Ubuntu (also Kali NetHunter proot):**

```bash
sudo apt update && sudo apt install python3 python3-venv rustc cargo protobuf-compiler git
```

**Termux (native, no root):**

```bash
pkg update
pkg install python rust git
```

`protoc` is only needed to *build* the Rust extension, not to run an installed wheel.
`protoc` فقط برای *ساخت* اکستنشن Rust لازم است، نه برای اجرای wheel نصب‌شده.

**xray-core binary:** Download the release matching `engine-core/xray-proto-pin.env` from [XTLS/xray-core](https://github.com/XTLS/xray-core/releases) and place it in `~/bin/xray` or any directory in your `$PATH`. Running a *different* xray version than the pin makes `bimarz doctor` print a mismatch warning.
**باینری xray-core:** نسخه‌ی مطابق با `engine-core/xray-proto-pin.env` را از [XTLS/xray-core](https://github.com/XTLS/xray-core/releases) دانلود کن و در `~/bin/xray` یا هر دایرکتوری داخل `$PATH` قرار بده. اجرای نسخه‌ی *متفاوت* از پین باعث می‌شود `bimarz doctor` هشدار ناهماهنگی چاپ کند.

---

## Quick Start / شروع سریع

If you already have all prerequisites:

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python3 -m venv .venv
source .venv/bin/activate
./scripts/build-release.sh
pip install engine-core/target/wheels/*.whl
bimarz doctor
```

`build-release.sh` fetches the pinned proto files itself, runs the same fmt/clippy gates as CI, builds the wheel and validates it.
`build-release.sh` خودش فایل‌های proto پین‌شده را واکشی می‌کند، همان گیت‌های fmt/clippy مربوط به CI را اجرا می‌کند، wheel را می‌سازد و اعتبارسنجی می‌کند.

---

## Step-by-Step / گام‌به‌گام

### Step 1 — Clone the repository / گام ۱ — کلون کردن ریپازیتوری

```bash
cd ~
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
```

### Step 2 — Fetch official proto files / گام ۲ — واکشی فایل‌های proto رسمی

These are **not** committed to the repo (they must match the exact xray-core version pinned in `engine-core/xray-proto-pin.env`):

```bash
./scripts/fetch-protos.sh
```

The script verifies the pinned immutable commit after cloning, so a moved upstream tag fails loudly instead of silently changing your build.
این اسکریپت بعد از clone، کامیت غیرقابل‌تغییر پین‌شده را بررسی می‌کند تا جابه‌جاشدن تگ upstream با خطای واضح متوقف شود به‌جای این‌که بی‌صدا build را عوض کند.

### Step 3 — Create virtual environment / گام ۳ — ساخت محیط مجازی

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **Tip / نکته:** Always activate the venv before running any `bimarz` command or `maturin` build. `build-release.sh` respects an already-active venv and otherwise uses the project `.venv` — it never installs into your global Python.
> **نکته:** همیشه قبل از اجرای هر دستور `bimarz` یا build با `maturin`، venv را فعال کن. `build-release.sh` به venv فعال احترام می‌گذارد و در غیر این صورت از `.venv` پروژه استفاده می‌کند — هرگز چیزی داخل پایتون سراسری نصب نمی‌کند.

### Step 4 — Build the Rust extension / گام ۴ — ساخت اکستنشن Rust

For development (editable install):

```bash
pip install "maturin>=1.8,<2.0"
maturin develop --release
```

For a release wheel:

```bash
./scripts/build-release.sh            # native arch
./scripts/build-release.sh --aarch64  # also cross-build aarch64 via zig
```

### Step 5 — Install the wheel / گام ۵ — نصب wheel

```bash
pip install engine-core/target/wheels/*.whl
```

If you also cross-built with `--aarch64`, pick the wheel matching your host arch instead of using the wildcard.
اگر با `--aarch64` هم کراس-بیلد گرفته‌ای، به‌جای wildcard همان wheelی را انتخاب کن که با معماری هاستت مطابقت دارد.

Or install a pre-built wheel from GitHub Releases that matches your Python version and architecture, e.g. the `cp313` + `x86_64` wheel for Python 3.13 on x86_64 glibc Linux.
یا wheel از پیش ساخته‌شده‌ی مطابق با نسخه‌ی پایتون و معماریت را از GitHub Releases نصب کن؛ مثلاً wheel مربوط به `cp313` و `x86_64` برای پایتون ۳.۱۳ روی لینوکس glibc معماری x86_64.

### Step 6 — Verify installation / گام ۶ — بررسی نصب

```bash
bimarz --version
bimarz doctor
```

Expected output (version numbers follow the installed release) / خروجی مورد انتظار (اعداد نسخه از ریلیز نصب‌شده پیروی می‌کنند):

```
bimarz doctor — version 0.2.2
✓ xray-core binary found: <PATH-resolved xray binary> (version: Xray 1.8.24)
● gRPC status: unreachable at 127.0.0.1:10085
Profiles stored: 0
○ Kill-switch is inactive
```

`unreachable` before your first connection is normal — it means nothing is listening on the gRPC port yet. See the gRPC status table below.
`unreachable` قبل از اولین اتصال طبیعی است — یعنی هنوز چیزی روی پورت gRPC گوش نمی‌دهد. جدول وضعیت‌های gRPC پایین را ببین.

---

## Platform Notes / نکات پلتفرم

These environments are **not equivalent** — do not assume a wheel built for one runs on the other:
این محیط‌ها **معادل هم نیستند** — فرض نکن wheel ساخته‌شده برای یکی روی دیگری اجرا می‌شود:

### Arch Linux (desktop)

- Full kernel-level kill-switch available with root access.
- Build with `CARGO_BUILD_JOBS=1` on low-RAM systems (e.g., Dell Inspiron 1525 with 2GB RAM).

### Kali NetHunter inside Termux (proot/chroot)

- This is a **glibc Linux userspace** (Kali) running on an Android kernel — `linux_aarch64` wheels and the native build both work here.
- Detected automatically via Android kernel mount signals.
- Kernel-level kill-switch is **not possible** without host root/CAP_NET_ADMIN — the software fallback activates automatically (see kill-switch section below).
- If `iptables: Failed to initialize nft: Permission denied` appears during tests, this is expected and harmless.

### Plain Termux (no NetHunter)

- Termux uses the **Android bionic libc**, not glibc. The pre-built `aarch64-unknown-linux-gnu` wheels — including the ones from GitHub Releases — **do not run in native Termux**. Build from source instead: `pkg install python rust git`, then follow the Step-by-Step section (maturin will produce a Termux-compatible module).
- Kernel-level kill-switch requires root on the device; without it the software fallback is used.
- Build may be slower due to limited RAM; use `CARGO_BUILD_JOBS=1`.

### WSL

- Full kernel-level kill-switch available with root access inside WSL.
- Ensure the `xray-core` binary is the Linux build, not the Windows one.

### Kill-switch modes / حالت‌های kill-switch

- **Kernel-level (iptables owner match):** real traffic blocking at the netfilter level. Requires root/CAP_NET_ADMIN; availability is detected with a *real* probe that inserts and removes a harmless iptables rule. xray-core's own UID is exempted so the tunnel itself is never blocked.
- **Software fallback (process watcher):** when kernel capability is unavailable, BiMarz runs a watcher thread that *detects* an unexpected xray-core exit and raises/triggers cleanup. This is a **best-effort detection mechanism — it does not block network traffic** and must not be relied on as a complete leak-proof kill switch.

---

## Troubleshooting / رفع مشکل

### `ImportError: cannot import name '_engine_core'`

The Rust extension is not built. Run:

```bash
source .venv/bin/activate
./scripts/fetch-protos.sh   # if you skipped Step 2
maturin develop --release
```

### `BinaryNotFoundError: xray-core binary not found`

Install xray-core or specify its path:

```bash
bimarz doctor --xray-bin /path/to/xray
```

### gRPC status meanings in `bimarz doctor`

| Status / وضعیت | Real meaning / معنای واقعی |
|---|---|
| `not_checked` | The probe did not run (e.g. check skipped). / probe اجرا نشده. |
| `unreachable` | TCP port probe failed — usually xray-core is not running (or the API is disabled/wrong host:port). / probe پورت TCP شکست خورد — معمولاً xray-core اجرا نشده. |
| `listening` | TCP port is open but no valid gRPC response — xray is accepting connections but the API call failed, or the Rust extension is not built (probe downgrades to TCP-only). / پورت باز است ولی پاسخ gRPC معتبر نیست. |
| `responding` | The gRPC API answered a real call — fully operational. / API مربوط به gRPC به یک فراخوانی واقعی پاسخ داده. |

### `warning: xray binary version ... does not match the proto bindings ...`

The running xray-core differs from the version pinned in `engine-core/xray-proto-pin.env`. Either install the matching xray release, or deliberately update the pin file, re-run `./scripts/fetch-protos.sh` and rebuild.
باینری xray در حال اجرا با نسخه‌ی پین‌شده در `engine-core/xray-proto-pin.env` فرق دارد. یا ریلیز مطابق را نصب کن، یا آگاهانه فایل پین را به‌روز کن، `./scripts/fetch-protos.sh` را دوباره اجرا کن و rebuild بگیر.

### Build fails with "too many leading super keywords"

The proto files were fetched incompletely. Re-run `./scripts/fetch-protos.sh` and ensure both `app/` and `common/` directories are copied fully.
فایل‌های proto ناقص واکشی شده‌اند. `./scripts/fetch-protos.sh` را دوباره اجرا کن و مطمئن شو هر دو دایرکتوری `app/` و `common/` کامل کپی شده‌اند.

### Permission denied during `cargo test` (iptables/nft)

Expected on non-root environments. The kill-switch capability probe needs root/netfilter access; the test suite tolerates its absence. This is not a code failure.
روی محیط‌های غیر root مورد انتظار است. probe مربوط به قابلیت kill-switch به دسترسی root/netfilter نیاز دارد؛ مجموعه تست نبودن آن را تحمل می‌کند. این خطای کد نیست.

---

## Uninstall / حذف نصب

Each step is independent — run only what you actually want to remove:
هر گام مستقل است — فقط چیزی را اجرا کن که واقعاً می‌خواهی حذف شود:

**1. Uninstall the package / حذف پکیج:**

```bash
source ~/bimarz/.venv/bin/activate
pip uninstall bimarz
```

**2. Remove the build environment / حذف محیط build:**

```bash
rm -rf ~/bimarz/.venv
```

**3. Remove the source tree / حذف درخت سورس:**

```bash
cd ~
rm -rf ~/bimarz
```

**4. Remove user data — ⚠️ irreversible / حذف داده‌های کاربر — ⚠️ غیرقابل بازگشت:**

This deletes your encrypted profiles, logs and cached state. There is no undo.
این کار پروفایل‌های رمزنگاری‌شده، لاگ‌ها و کش وضعیت را حذف می‌کند. راه برگشتی نیست.

```bash
rm -rf ~/.config/bimarz
```

**5. Remove the xray-core binary (only if you installed it manually) / حذف باینری xray-core (فقط اگر دستی نصبش کرده‌ای):**

```bash
rm ~/bin/xray
```

---

*Last updated / آخرین به‌روزرسانی: 2026-08-17*
