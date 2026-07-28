# BiMarz (بی‌مرز)

**یک لایه‌ی مدیریتی حرفه‌ای دور باینری Xray-core، ساخته‌شده برای شرایط سخت‌گیرانه‌ی فیلترینگ در ایران (و قابل استفاده در هر جای دنیا).**
**A professional management layer around the Xray-core binary, built for Iran's demanding filtering conditions (and usable anywhere in the world).**

[فارسی](#فارسی) | [English](#english)

> ⚠️ **وضعیت فعلی پروژه:** این پروژه در **فاز ۱ از ۸** نقشه راه است. فقط دستور `bimarz doctor` و اسکلت اتصال gRPC آماده‌اند. جزئیات کامل در بخش «وضعیت و نقشه راه» پایین همین صفحه.
> ⚠️ **Current project status:** this project is at **phase 1 of 8** on the roadmap. Only `bimarz doctor` and the gRPC connection skeleton exist so far. Full details in the "Status & Roadmap" section below.

---

## فارسی

### این پروژه چیست؟

`bimarz` قصد ندارد پروتکل رمزنگاری یا مبهم‌سازی بسازد — این کار توسط تیم
[Xray-core](https://github.com/XTLS/xray-core) به بهترین شکل انجام شده و
سال‌ها در میدان واقعی تست شده است. کاری که `bimarz` انجام می‌دهد، ساختن یک
لایه‌ی مدیریتی حرفه‌ای *دور* آن باینری‌ست:

- مدیریت چند پروفایل سرور بدون نیاز به ویرایش دستی فایل JSON
- تست خودکار سلامت سرورها و سوییچ بی‌وقفه به بهترین گزینه (failover)
- Kill-switch سطح سیستم تا در صورت قطع تونل، هیچ ترافیکی لو نرود
- جلوگیری از نشت DNS
- یک CLI واحد و ساده، با پیام‌های خطای دقیق و قابل‌فهم

### چرا این معماری؟

| لایه | زبان | چرا |
|---|---|---|
| اتصال gRPC به xray-core، health-check موازی، kill-switch | **Rust** | کارایی و ایمنی حافظه برای صدها اتصال همزمان و مدیریت دقیق شبکه |
| CLI، مدیریت پروفایل، پارس subscription | **Python** | سرعت توسعه، خوانایی، تجربه‌ی از قبل اثبات‌شده در پروژه‌ی [open-downloader-cli](https://github.com/msoleimani62/open-downloader-cli) |

جزئیات کامل تصمیمات معماری در فایل نقشه راه پروژه (که در ابتدای همکاری تهیه
شد) و در `CHANGELOG.md` مستند شده‌اند.

### وضعیت و نقشه راه

| فاز | عنوان | وضعیت |
|---|---|---|
| ۰ | اثبات مفهوم gRPC | ✅ راهنمای دستی آماده (`engine-core/proto/README.md`) |
| ۱ | Engine Adapter (اتصال gRPC پایه) | 🚧 اسکلت آماده، پیام‌های gRPC هنوز به proto واقعی وصل نشده‌اند |
| ۲ | مدیریت پروفایل و Subscription | ⏳ شروع نشده |
| ۳ | Health-check و Failover خودکار | ⏳ شروع نشده |
| ۴ | Kill-switch و ضدنشت DNS | ⏳ شروع نشده |
| ۵ | تکمیل CLI و بسته‌بندی | ⏳ شروع نشده |
| ۶ | تست و CI کامل | 🚧 اسکلت CI آماده، هنوز کامل تایید نشده |
| ۷ | رابط گرافیکی دسکتاپ | ⏳ شروع نشده |
| ۸ | اپ اندروید | ⏳ شروع نشده |

جزئیات فنی هر تغییر در [`CHANGELOG.md`](./CHANGELOG.md) ثبت می‌شود.

### نصب (از سورس — هنوز منتشر نشده)

این پروژه هنوز به‌صورت پکیج آماده منتشر نشده. نصب فعلی فقط برای توسعه است.

```bash
# ۱. کلون کردن ریپازیتوری
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz

# ۲. واکشی فایل‌های proto رسمی xray-core (نیاز به اینترنت)
#    دستورهای دقیق در engine-core/proto/README.md
cat engine-core/proto/README.md

# ۳. نصب Rust (اگر از قبل نصب نیست)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# ۴. ساخت محیط مجازی پایتون و نصب ابزار build
python3 -m venv .venv
source .venv/bin/activate
pip install maturin

# ۵. ساخت و نصب پکیج (شامل کامپایل بخش Rust)
maturin develop --release

# ۶. تست نصب
bimarz doctor
```

### استفاده

فعلاً فقط دستور تشخیصی زیر پیاده‌سازی شده:

```bash
bimarz doctor                       # بررسی کامل محیط، باینری xray-core و وضعیت پروفایل‌ها
bimarz doctor --xray-bin /path/xray # مسیر صریح باینری xray-core
bimarz --debug doctor               # نمایش کامل خطای فنی در صورت بروز مشکل
```

### پلتفرم‌های پشتیبانی‌شده

| پلتفرم | وضعیت تشخیص خودکار | یادداشت |
|---|---|---|
| آرچ لینوکس (دسکتاپ) | ✅ | محیط توسعه‌ی اصلی پروژه |
| کالی NetHunter داخل Termux (proot/chroot) | ✅ | تشخیص از طریق نشانه‌های mount کرنل اندروید؛ توجه: kill-switch کامل در این محیط بدون روت هاست ممکن نیست (فاز ۴) |
| ترموکس ساده (بدون NetHunter) | ✅ | |
| WSL | ✅ | |
| سایر توزیع‌های لینوکس | عمومی | باید به‌عنوان `desktop_linux`/`other` شناسایی شود |

### مشارکت

Issue ها و Pull Request ها در ریپازیتوری GitHub پروژه پذیرفته می‌شوند. لطفاً
قبل از هر PR، `ruff check`/`ruff format`/`cargo clippy`/`cargo test` را
اجرا و سبز کنید.

### مجوز

MIT — فایل `LICENSE` را ببینید.

---

## English

### What is this?

`bimarz` does not attempt to build a new encryption or obfuscation protocol —
that job is already done exceptionally well by the
[Xray-core](https://github.com/XTLS/xray-core) team and has been
battle-tested for years. What `bimarz` builds is a professional management
layer *around* that binary:

- Managing multiple server profiles without hand-editing JSON
- Automatic health-checking with seamless failover to the best server
- A system-level kill-switch so no traffic leaks if the tunnel drops
- DNS leak protection
- A single, coherent CLI with precise, understandable error messages

### Why this architecture?

| Layer | Language | Why |
|---|---|---|
| gRPC connection to xray-core, parallel health-checks, kill-switch | **Rust** | Performance and memory safety for hundreds of concurrent connections and precise network handling |
| CLI, profile management, subscription parsing | **Python** | Development speed, readability, a pattern already proven in [open-downloader-cli](https://github.com/msoleimani62/open-downloader-cli) |

Full architectural reasoning is documented in the project's roadmap
document (produced at project kickoff) and in `CHANGELOG.md`.

### Status & Roadmap

| Phase | Title | Status |
|---|---|---|
| 0 | gRPC proof-of-concept | ✅ Manual guide ready (`engine-core/proto/README.md`) |
| 1 | Engine Adapter (base gRPC connection) | 🚧 Skeleton ready; gRPC messages not yet wired to real proto |
| 2 | Profile & Subscription Manager | ⏳ Not started |
| 3 | Health-check & automatic Failover | ⏳ Not started |
| 4 | Kill-switch & DNS leak guard | ⏳ Not started |
| 5 | CLI polish & packaging | ⏳ Not started |
| 6 | Full test suite & CI | 🚧 CI skeleton ready, not yet fully verified |
| 7 | Desktop GUI | ⏳ Not started |
| 8 | Android app | ⏳ Not started |

Every technical change is logged in [`CHANGELOG.md`](./CHANGELOG.md).

### Installation (from source — not yet published)

This project is not published as a ready-made package yet. Current
installation is for development only.

```bash
# 1. Clone the repository
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz

# 2. Fetch the official xray-core proto files (needs internet)
#    Exact steps in engine-core/proto/README.md
cat engine-core/proto/README.md

# 3. Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 4. Create a Python virtual environment and install the build tool
python3 -m venv .venv
source .venv/bin/activate
pip install maturin

# 5. Build and install the package (compiles the Rust part too)
maturin develop --release

# 6. Verify the install
bimarz doctor
```

### Usage

Only the diagnostic command is implemented so far:

```bash
bimarz doctor                       # full check of environment, xray-core binary, and profile status
bimarz doctor --xray-bin /path/xray # explicit path to the xray-core binary
bimarz --debug doctor                # show full technical traceback on failure
```

### Supported platforms

| Platform | Auto-detection status | Notes |
|---|---|---|
| Arch Linux (desktop) | ✅ | Primary development environment |
| Kali NetHunter inside Termux (proot/chroot) | ✅ | Detected via Android kernel mount signals; note: a full kill-switch is not possible in this environment without host root (phase 4) |
| Plain Termux (no NetHunter) | ✅ | |
| WSL | ✅ | |
| Other Linux distros | Generic | Should detect as `desktop_linux`/`other` |

### Contributing

Issues and Pull Requests are welcome on the project's GitHub repository.
Please run `ruff check`/`ruff format`/`cargo clippy`/`cargo test` clean
before opening a PR.

### License

MIT — see the `LICENSE` file.
