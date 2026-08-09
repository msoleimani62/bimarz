# BiMarz (بی‌مرز)

**یک لایه‌ی مدیریتی حرفه‌ای دور باینری Xray-core، ساخته‌شده برای شرایط سخت‌گیرانه‌ی فیلترینگ در ایران (و قابل استفاده در هر جای دنیا).**  
**A professional management layer around the Xray-core binary, built for Iran's demanding filtering conditions (and usable anywhere in the world).**

[فارسی](#فارسی) | [English](#english)

> ⚠️ **وضعیت فعلی پروژه:** فازهای **۰ تا ۵ از ۸** نقشه راه کامل و به‌صورت end-to-end روی سخت‌افزار واقعی تایید شده‌اند. فاز ۶ (تست و CI کامل) در حال انجام است. فاز ۷ (GUI دسکتاپ) شروع شده و اسکلت اولیه‌ی PySide6 پیاده‌سازی شده است. فاز ۸ (اپ اندروید) هنوز شروع نشده است. جزئیات کامل در بخش «وضعیت و نقشه راه».
> ⚠️ **Current project status:** phases **0 through 5 of 8** on the roadmap are complete and verified end-to-end on real hardware. Phase 6 (full test suite & CI) is in progress. Phase 7 (Desktop GUI) has started and the initial PySide6 skeleton is implemented. Phase 8 (Android app) is not started yet. Full details in the "Status & Roadmap" section below.

---

## فارسی

### این پروژه چیست؟

`bimarz` قصد ندارد پروتکل رمزنگاری یا مبهم‌سازی بسازد — این کار توسط تیم [Xray-core](https://github.com/XTLS/xray-core) به بهترین شکل انجام شده و سال‌ها در میدان واقعی تست شده است. کاری که `bimarz` انجام می‌دهد، ساختن یک لایه‌ی مدیریتی حرفه‌ای *دور* آن باینری‌ست:

- مدیریت چند پروفایل سرور بدون نیاز به ویرایش دستی فایل JSON
- تست خودکار سلامت سرورها و سوییچ بی‌وقفه به بهترین گزینه (failover)
- Kill-switch سطح سیستم تا در صورت قطع تونل، هیچ ترافیکی لو نرود (با fallback نرم‌افزاری صادقانه در محیط‌هایی مثل Termux/proot که دسترسی کرنل کامل ندارند)
- جلوگیری از نشت DNS با اجبار DNS-over-HTTPS از طریق خودِ تونل
- یک CLI واحد و ساده، با پیام‌های خطای دقیق و قابل‌فهم
- GUI دسکتاپ (PySide6) در فاز ۷

### چرا این معماری؟

| لایه | زبان | مسئولیت | چرا |
|---|---|---|---|
| Engine Adapter | **Rust** | اتصال gRPC به xray-core، health-check موازی، kill-switch، DNS guard | کارایی و ایمنی حافظه برای صدها اتصال همزمان و مدیریت دقیق شبکه |
| Orchestrator | **Python** | CLI، مدیریت پروفایل، پارس subscription، منطق failover، GUI | سرعت توسعه، خوانایی، تجربه‌ی از قبل اثبات‌شده |

جزئیات کامل تصمیمات معماری و باگ‌های واقعی که در طول توسعه پیدا و رفع شدند (از جمله یک باگ حیاتی routing و یک باگ حیاتی UID در kill-switch) در `CHANGELOG.md` مستند شده‌اند.

### معماری ماژولار فعلی

```
┌─────────────────────────────────────────────┐
│  CLI (argparse) — orchestrator/bimarz/cli.py │
│  فقط _build_parser() و main() (~۱۱۷ خط)      │
├─────────────────────────────────────────────┤
│  commands/  — یک فایل به‌ازای هر زیر-دستور    │
│  doctor.py | profile.py | healthcheck.py     │
│  connect.py | killswitch.py                  │
├─────────────────────────────────────────────┤
│  services/  — منطق تجاری، مستقل از CLI/GUI   │
│  doctor | profile | health | process         │
│  engine | killswitch | failover              │
├─────────────────────────────────────────────┤
│  connection.py — ConnectionService (CM)      │
│  config.py — AppConfig (env > default)       │
│  events.py — Event system                    │
│  protocols.py — DI Protocols                 │
│  helpers.py — Stateless helpers              │
├─────────────────────────────────────────────┤
│  gui/ — PySide6 desktop (phase 7 skeleton)   │
├─────────────────────────────────────────────┤
│  engine-core (Rust) — PyO3 async bridge      │
├─────────────────────────────────────────────┤
│  Binary Xray-core (external process)         │
└─────────────────────────────────────────────┘
```

### وضعیت و نقشه راه

| فاز | عنوان | وضعیت | توضیح |
|---|---|---|---|
| ۰ | اثبات مفهوم gRPC | ✅ کامل | اتصال اولیه به API محلی xray-core |
| ۱ | Engine Adapter | ✅ کامل | gRPC واقعی: add/remove outbound، get stats |
| ۲ | مدیریت پروفایل و Subscription | ✅ کامل | پارس VLESS+Reality، ذخیره‌ی رمزنگاری‌شده (PBKDF2+Fernet) |
| ۳ | Health-check و Failover خودکار | ✅ کامل | `bimarz healthcheck`، `bimarz connect --auto-failover` |
| ۴ | Kill-switch و ضدنشت DNS | ✅ کامل | `bimarz killswitch`، software fallback در Termux |
| ۵ | تکمیل CLI و بسته‌بندی | ✅ کامل | doctor لایه‌ای، release workflow، build script، refactor ماژولار cli.py |
| ۶ | تست و CI کامل | 🚧 در حال انجام | CI پایه آماده (ruff+pytest+cargo)، integration test با xray-core واقعی در حال تکمیل |
| ۷ | رابط گرافیکی دسکتاپ | 🚧 شروع شده | PySide6، فقط لایه نمایش، بدون تکرار منطق |
| ۸ | اپ اندروید | ⏳ شروع نشده | Kotlin + uniffi-rs، بدون fork منطق engine |

جزئیات فنی هر تغییر در [`CHANGELOG.md`](./CHANGELOG.md) ثبت می‌شود.

### پیش‌نیازها

| ابزار | حداقل نسخه | یادداشت |
|---|---|---|
| Python | ۳.۱۰+ | با venv |
| Rust | ۱.۷۸+ | برای کامپایل engine-core |
| xray-core | ۱.۸.۲۴ | باینری در PATH یا مسیر صریح با `--xray-bin` |
| maturin | ۱.۷+ | برای ساخت پل PyO3 |
| (اختیاری) PySide6 | ۶.۷+ | فقط برای GUI دسکتاپ |

### نصب (از سورس)

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz

# ۱. واکشی proto های رسمی xray-core
XRAY_TAG="v1.8.24"
git clone --depth 1 --branch "$XRAY_TAG"     https://github.com/XTLS/xray-core.git /tmp/xray-core-src
mkdir -p engine-core/proto
cp -r /tmp/xray-core-src/app engine-core/proto/
cp -r /tmp/xray-core-src/common engine-core/proto/
rm -rf /tmp/xray-core-src

# ۲. ساخت محیط مجازی و نصب
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip maturin
maturin develop --release

# ۳. بررسی نصب
bimarz doctor
```

### استفاده

```bash
# تشخیص محیط و سلامت
bimarz doctor                          # بررسی کامل
bimarz doctor --xray-bin /path/xray    # مسیر صریح باینری
bimarz --debug doctor                  # نمایش traceback کامل

# مدیریت پروفایل
bimarz profile add "vless://..."       # افزودن از لینک VLESS+Reality+Vision
bimarz profile list                    # نمایش پروفایل‌ها
bimarz profile remove <id>             # حذف با شناسه

# تست سلامت
bimarz healthcheck                     # تست موازی همه‌ی پروفایل‌ها

# اتصال
bimarz connect <id>                              # اتصال ساده
bimarz connect <id> --auto-failover              # failover خودکار
bimarz connect <id> --killswitch                 # kill-switch فعال
bimarz connect <id> --auto-failover --killswitch # همه با هم

# kill-switch دستی
bimarz killswitch enable --xray-uid $(id -u)
bimarz killswitch disable
bimarz killswitch status
```

**رمزنگاری پروفایل‌ها:** پروفایل‌ها با PBKDF2-HMAC-SHA256 → Fernet رمزنگاری می‌شوند. اولین پسورد ثابت می‌شود. برای اسکریپت‌نویسی/CI متغیر `BIMARZ_PROFILE_PASSWORD` را تنظیم کن.

### پلتفرم‌های پشتیبانی‌شده

| پلتفرم | تشخیص خودکار | kill-switch | یادداشت |
|---|---|---|---|
| Arch Linux (دسکتاپ) | ✅ | سطح کرنل (با روت) | محیط توسعه اصلی |
| Kali NetHunter + Termux | ✅ | software fallback | chroot/proot، بدون روت هاست |
| Termux ساده | ✅ | software fallback | |
| WSL | ✅ | سطح کرنل (با روت) | |
| سایر لینوکس | عمومی | بستگی به محیط | `desktop_linux` / `other` |

### حذف نصب

```bash
source .venv/bin/activate
pip uninstall bimarz
rm -rf ~/.config/bimarz          # داده‌های کاربر (پروفایل‌ها، لاگ)
rm -rf ~/bimarz/.venv            # محیط مجازی
cd ~ && rm -rf ~/bimarz          # سورس (اختیاری)
```

### مشارکت

Issue و Pull Request در [GitHub](https://github.com/msoleimani62/bimarz) پذیرفته می‌شود. قبل از هر PR:

```bash
source .venv/bin/activate
ruff check orchestrator tests
ruff format --check orchestrator tests
pytest
cd engine-core && cargo test && cargo clippy --all-targets -- -D warnings
```

### مجوز

MIT — فایل [`LICENSE`](./LICENSE) را ببینید.

---

## English

### What is this?

`bimarz` does not attempt to build a new encryption or obfuscation protocol — that job is already done exceptionally well by the [Xray-core](https://github.com/XTLS/xray-core) team and has been battle-tested for years. What `bimarz` builds is a professional management layer *around* that binary:

- Managing multiple server profiles without hand-editing JSON
- Automatic health-checking with seamless failover to the best server
- A system-level kill-switch so no traffic leaks if the tunnel drops (with an honest software fallback in environments like Termux/proot that lack full kernel access)
- DNS leak protection by forcing DNS-over-HTTPS through the tunnel itself
- A single, coherent CLI with precise, understandable error messages
- Desktop GUI (PySide6) in phase 7

### Why this architecture?

| Layer | Language | Responsibility | Why |
|---|---|---|---|
| Engine Adapter | **Rust** | gRPC to xray-core, parallel health-checks, kill-switch, DNS guard | Performance and memory safety for hundreds of concurrent connections |
| Orchestrator | **Python** | CLI, profile management, subscription parsing, failover logic, GUI | Development speed, readability, proven pattern |

Full architectural reasoning, and real bugs found and fixed during development (including a critical routing bug and a critical kill-switch UID bug), are documented in `CHANGELOG.md`.

### Current Modular Architecture

```
┌─────────────────────────────────────────────┐
│  CLI (argparse) — orchestrator/bimarz/cli.py │
│  Only _build_parser() and main() (~117 loc)  │
├─────────────────────────────────────────────┤
│  commands/  — one file per CLI sub-command   │
│  doctor.py | profile.py | healthcheck.py     │
│  connect.py | killswitch.py                  │
├─────────────────────────────────────────────┤
│  services/  — business logic, CLI/GUI agnostic│
│  doctor | profile | health | process         │
│  engine | killswitch | failover              │
├─────────────────────────────────────────────┤
│  connection.py — ConnectionService (CM)      │
│  config.py — AppConfig (env > default)       │
│  events.py — Event system                    │
│  protocols.py — DI Protocols                 │
│  helpers.py — Stateless helpers              │
├─────────────────────────────────────────────┤
│  gui/ — PySide6 desktop (phase 7 skeleton)   │
├─────────────────────────────────────────────┤
│  engine-core (Rust) — PyO3 async bridge      │
├─────────────────────────────────────────────┤
│  Binary Xray-core (external process)         │
└─────────────────────────────────────────────┘
```

### Status & Roadmap

| Phase | Title | Status | Notes |
|---|---|---|---|
| 0 | gRPC proof-of-concept | ✅ Complete | Initial local API connection |
| 1 | Engine Adapter | ✅ Complete | Real gRPC: add/remove outbound, get stats |
| 2 | Profile & Subscription Manager | ✅ Complete | VLESS+Reality parsing, encrypted storage (PBKDF2+Fernet) |
| 3 | Health-check & automatic Failover | ✅ Complete | `bimarz healthcheck`, `bimarz connect --auto-failover` |
| 4 | Kill-switch & DNS leak guard | ✅ Complete | `bimarz killswitch`, software fallback on Termux |
| 5 | CLI polish & packaging | ✅ Complete | Layered doctor, release workflow, build script, modular cli.py refactor |
| 6 | Full test suite & CI | 🚧 In progress | Base CI ready (ruff+pytest+cargo), real xray-core integration test being finalized |
| 7 | Desktop GUI | 🚧 Started | PySide6, display layer only, no logic duplication |
| 8 | Android app | ⏳ Not started | Kotlin + uniffi-rs, no engine logic fork |

Every technical change is logged in [`CHANGELOG.md`](./CHANGELOG.md).

### Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.10+ | with venv |
| Rust | 1.78+ | to compile engine-core |
| xray-core | 1.8.24 | binary in PATH or explicit `--xray-bin` |
| maturin | 1.7+ | for building the PyO3 bridge |
| (optional) PySide6 | 6.7+ | desktop GUI only |

### Installation (from source)

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz

# 1. Fetch official xray-core proto files
XRAY_TAG="v1.8.24"
git clone --depth 1 --branch "$XRAY_TAG"     https://github.com/XTLS/xray-core.git /tmp/xray-core-src
mkdir -p engine-core/proto
cp -r /tmp/xray-core-src/app engine-core/proto/
cp -r /tmp/xray-core-src/common engine-core/proto/
rm -rf /tmp/xray-core-src

# 2. Build virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip maturin
maturin develop --release

# 3. Verify installation
bimarz doctor
```

### Usage

```bash
# Environment diagnostics
bimarz doctor                          # full check
bimarz doctor --xray-bin /path/xray    # explicit binary path
bimarz --debug doctor                  # show full traceback on failure

# Profile management
bimarz profile add "vless://..."       # add from VLESS+Reality+Vision link
bimarz profile list                    # list saved profiles
bimarz profile remove <id>             # remove by id

# Health check
bimarz healthcheck                     # parallel check all profiles

# Connection
bimarz connect <id>                              # simple connect
bimarz connect <id> --auto-failover              # auto failover
bimarz connect <id> --killswitch                 # enable kill-switch
bimarz connect <id> --auto-failover --killswitch # both together

# Manual kill-switch
bimarz killswitch enable --xray-uid $(id -u)
bimarz killswitch disable
bimarz killswitch status
```

**Profile encryption:** Profiles are encrypted with PBKDF2-HMAC-SHA256 → Fernet. The first password you enter becomes permanent. For scripting/CI, set the `BIMARZ_PROFILE_PASSWORD` environment variable instead of being prompted interactively.

### Supported platforms

| Platform | Auto-detection | Kill-switch | Notes |
|---|---|---|---|
| Arch Linux (desktop) | ✅ | Kernel-level (with root) | Primary dev environment |
| Kali NetHunter + Termux | ✅ | Software fallback | chroot/proot, no host root |
| Plain Termux | ✅ | Software fallback | |
| WSL | ✅ | Kernel-level (with root) | |
| Other Linux distros | Generic | Environment-dependent | `desktop_linux` / `other` |

### Uninstall

```bash
source .venv/bin/activate
pip uninstall bimarz
rm -rf ~/.config/bimarz          # user data (profiles, logs)
rm -rf ~/bimarz/.venv            # virtual environment
cd ~ && rm -rf ~/bimarz          # source (optional)
```

### Contributing

Issues and Pull Requests are welcome on [GitHub](https://github.com/msoleimani62/bimarz). Before opening a PR:

```bash
source .venv/bin/activate
ruff check orchestrator tests
ruff format --check orchestrator tests
pytest
cd engine-core && cargo test && cargo clippy --all-targets -- -D warnings
```

### License

MIT — see the [`LICENSE`](./LICENSE) file.
