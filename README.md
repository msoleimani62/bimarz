# 🐉 BiMarz — Cross-Platform Xray/VLESS Reality Orchestrator

**BiMarz (بی‌مرز)** یک لایه orchestration چندسکویی برای مدیریت اتصال‌های **Xray/VLESS + Reality + XTLS Vision** است که با معماری ترکیبی **Python + Rust** طراحی شده است.

BiMarz لایه orchestration سطح بالا را در Python نگه می‌دارد و قابلیت‌های engine و عملیات سطح پایین را در Rust پیاده‌سازی می‌کند. این معماری برای ایجاد یک سیستم قابل‌اعتماد، تست‌پذیر، امن و قابل توسعه برای مدیریت profileها، اتصال‌ها، health monitoring، failover، DNS leak protection و kill switch طراحی شده است.

[🇮🇷 فارسی](#فارسی) | [🇬🇧 English](#english)

> **وضعیت فعلی پروژه:** فازهای ۰ تا ۷ کامل شده‌اند. فاز ۸ در حال انجام است و روی hardening چرخه کامل اتصال، rollback، cleanup و شواهد پذیرش تمرکز دارد. وضعیت دقیق هر فاز در بخش Roadmap و وضعیت implementation واقعی در repository مرجع است.

---

## 🇮🇷 فارسی

### 📖 معرفی

BiMarz یک ابزار orchestration و مدیریت برای **xray-core** است که مسئولیت‌ها را میان دو لایه اصلی تقسیم می‌کند:

- **Python**: orchestration، مدیریت profile، subscription، health check، failover، DNS، CLI و GUI
- **Rust**: engine، ساخت ساختارهای موردنیاز xray-core، validation سطح پایین و ارتباط engine با xray-core

مرز میان این دو لایه از طریق **PyO3** تعریف شده است.

هدف اصلی پروژه ایجاد یک معماری چندسکویی و قابل تست برای مدیریت اتصال‌های VLESS، Reality و XTLS Vision است.

### ✨ قابلیت‌ها

- پشتیبانی از VLESS
- پشتیبانی از Reality
- پشتیبانی از XTLS Vision
- parser برای VLESS share link
- استخراج پارامترهای VLESS و Reality
- ساخت outbound موردنیاز xray-core
- ارتباط gRPC با xray-core
- Health Check
- Failover
- مدیریت profileهای سرور
- مدیریت subscription در بخش‌های پیاده‌سازی‌شده
- ذخیره‌سازی امن profileها در بخش‌های پیاده‌سازی‌شده
- DNS Leak Protection
- Kill Switch
- CLI
- رابط گرافیکی مبتنی بر PySide6
- Rust engine با PyO3
- تست‌های Python و Rust
- تست‌های unit و integration
- lint و formatting
- CI/CD و workflowهای مرتبط با build، test و release
- بررسی امنیتی dependencyها با cargo-audit، pip-audit و bandit

### 🏗️ معماری

```text
                         ┌────────────────────────────┐
                         │         BiMarz CLI         │
                         └──────────────┬─────────────┘
                                        │
                         ┌──────────────▼─────────────┐
                         │     Python Orchestrator    │
                         │                            │
                         │ profiles                   │
                         │ subscriptions              │
                         │ health / failover          │
                         │ DNS / kill switch          │
                         │ CLI / GUI                  │
                         └──────────────┬─────────────┘
                                        │ PyO3
                         ┌──────────────▼─────────────┐
                         │        Rust Engine         │
                         │        engine-core         │
                         └──────────────┬─────────────┘
                                        │ gRPC
                         ┌──────────────▼─────────────┐
                         │          xray-core         │
                         └────────────────────────────┘
```

Python مسئول orchestration و منطق سطح بالا است و Rust مسئول engine و عملیات سطح پایین است. این مرزبندی از تکرار منطق business در GUI و CLI جلوگیری کرده و boundary مشخصی میان orchestration و engine ایجاد می‌کند.

### 📁 معماری ماژولار

ساختار کلی repository به‌صورت زیر است:

```text
bimarz/
├── orchestrator/
│   └── bimarz/
│       ├── cli/
│       ├── gui/
│       ├── parsers/
│       ├── services/
│       ├── models/
│       ├── dns_leak_guard.py
│       ├── xray_config.py
│       └── ...
├── engine-core/
│   └── src/
│       ├── vless_builder.rs
│       ├── grpc_client.rs
│       └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── ...
├── proto/
├── .github/
│   └── workflows/
├── pyproject.toml
├── Cargo.toml
├── SECURITY.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

> ساختار بالا نمای کلی repository است. برای جزئیات دقیق، ساختار واقعی فایل‌های repository و source of truthهای پروژه مرجع اصلی هستند.

### 🗺️ نقشه راه

| فاز | وضعیت | توضیحات |
|---|---|---|
| ۰ | ✅ کامل | اسکلت اولیه، build system و proto fetch |
| ۱ | ✅ کامل | Rust engine-core، gRPC client و VLESS builder |
| ۲ | ✅ کامل | Profile & Subscription Manager و encrypted storage |
| ۳ | ✅ کامل | Connection orchestration، health check و failover |
| ۴ | ✅ کامل | Kill switch، DNS leak protection و platform detection |
| ۵ | ✅ کامل | CLI نهایی، GUI skeleton، packaging و release workflow |
| ۶ | ✅ کامل | CI/CD، security audit، quality gates و docs/INSTALL.md |
| ۷ | ✅ کامل | Subscription URL parsing، base64 decoding و auto-update profiles |
| ۸ | ✅ کامل | Connection lifecycle hardening، transactional rollback، cleanup observability و acceptance validation |
| ۹ | 🚧 شروع شده | اپلیکیشن اندروید (Kotlin + Jetpack Compose + uniffi-rs). فقط اسکلت اولیه — هنوز روی هیچ دستگاه واقعی build/test نشده. جزئیات: [`android/README.md`](android/README.md) |

> **نکته:** وضعیت roadmap باید با implementation واقعی repository هماهنگ بماند. برنامه‌های آینده نباید به‌عنوان قابلیت فعلی مستند شوند.

### ⚙️ پیش‌نیازها

| ابزار | وضعیت | توضیح |
|---|---|---|
| Python | 3.12+ | محیط اجرای orchestration |
| Rust | stable toolchain | ساخت engine-core |
| Cargo | stable | build و test بخش Rust |
| maturin | نسخه سازگار با pyproject.toml | build رابط PyO3 |
| xray-core | مطابق configuration پروژه | engine خارجی موردنیاز برای اتصال واقعی |
| Git | نسخه سازگار سیستم | دریافت و مدیریت repository |

نسخه‌های دقیق dependencyها باید از `pyproject.toml`، `Cargo.toml` و lock/configurationهای repository استخراج شوند و README نباید نسخه‌ای را بدون تطبیق با source of truth تثبیت کند.

### 🛰️ xray-core

BiMarz برای اجرای واقعی اتصال‌ها به **xray-core** نیاز دارد. پروژه مسئول نصب خودکار xray-core نیست و روش نصب باید متناسب با سیستم‌عامل و configuration فعلی انتخاب شود.

پس از نصب xray-core، وضعیت محیط را با دستور زیر بررسی کنید:

```bash
bimarz doctor
```

در صورتی که `doctor` executable یا وضعیت xray-core را گزارش کند، خروجی آن مرجع اصلی تشخیص محیط اجرایی خواهد بود.

### 📦 نصب از سورس

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install maturin
maturin develop --release
```

در صورتی که repository به dependency یا proto خارجی مشخصی نیاز داشته باشد، روش build باید مطابق `pyproject.toml`، `Cargo.toml` و documentation فعلی repository انجام شود.

### 🔨 ساخت Rust Extension

```bash
maturin develop --release
```

این دستور bridge مربوط به Rust/PyO3 را در محیط توسعه build می‌کند.

### 🩺 بررسی سلامت نصب

پس از نصب:

```bash
bimarz doctor
```

برای مشاهده گزینه‌های کامل:

```bash
bimarz doctor --help
```

در صورتی که نسخه فعلی CLI گزینه `--xray-bin` را ارائه کند، می‌توان مسیر صریح executable را نیز از طریق همان option مشخص کرد.

### 👤 مدیریت Profile

BiMarz اطلاعات اتصال را در قالب server profile مدیریت می‌کند.

دستورهای اصلی:

```bash
bimarz profile --help
bimarz profile list
bimarz profile add "vless://..."
bimarz profile remove <id>
```

پشتیبانی دقیق commandها و argumentها باید با `bimarz profile --help` در نسخه نصب‌شده بررسی شود.

### 🔐 رمزنگاری Profile

در implementation مربوط به encrypted profile storage، داده‌های profile با زنجیره رمزنگاری مبتنی بر **PBKDF2-HMAC-SHA256** و **Fernet** محافظت می‌شوند.

برای محیط‌های scripting و CI، در صورتی که implementation فعلی این متغیر را پشتیبانی کند، می‌توان credential موردنیاز را از طریق:

```bash
export BIMARZ_PROFILE_PASSWORD="..."
```

تأمین کرد.

> هرگز password، UUID، Reality private key یا سایر credentialهای واقعی را در repository، issue، log عمومی یا README قرار ندهید.

### 🔗 VLESS Share Link

BiMarz می‌تواند VLESS share link را parse کرده و پارامترهای پشتیبانی‌شده را استخراج کند.

پارامترهای قابل استخراج بسته به implementation می‌توانند شامل موارد زیر باشند:

- UUID
- server address
- port
- flow
- security
- SNI
- fingerprint
- Reality public key (`pbk`)
- Reality short ID (`sid`)
- spiderX (`spx`)
- network type
- path
- host
- ALPN
- سایر پارامترهای پشتیبانی‌شده parser

نمونه:

```text
vless://UUID@example.com:443?type=tcp&security=reality&sni=example.com&fp=chrome&pbk=PUBLIC_KEY&sid=SHORT_ID&flow=xtls-rprx-vision#My-Server
```

> مقادیر نمونه placeholder هستند و credential واقعی محسوب نمی‌شوند.

### 🚀 اتصال

نمونه‌های اصلی استفاده:

```bash
bimarz connect --help
bimarz connect <id>
bimarz connect <id> --auto-failover
bimarz connect <id> --killswitch
bimarz connect <id> --auto-failover --killswitch
```

BiMarz هنگام اتصال configuration موردنیاز xray-core را آماده کرده و outbound فعال را مدیریت می‌کند.

اگر syntax یا optionهای command در نسخه فعلی تغییر کرده باشد، خروجی `bimarz connect --help` مرجع نهایی است.

### ❤️ Health Check

```bash
bimarz healthcheck --help
bimarz healthcheck
```

Health Check برای بررسی وضعیت endpointها و سلامت مسیرهای مدیریت‌شده استفاده می‌شود. در implementation فعلی، health checks می‌توانند به‌صورت موازی برای profileهای مدیریت‌شده اجرا شوند.

### 🔄 Failover

Failover در صورت از دسترس خارج شدن مسیر فعال می‌تواند بر اساس policyهای موجود مسیر مناسب بعدی را انتخاب کند.

نمونه:

```bash
bimarz connect <id> --auto-failover
```

thresholdها، policyها و شرایط دقیق تغییر مسیر باید مطابق implementation و CLI نسخه فعلی بررسی شوند.

### 🛡️ DNS Leak Protection

BiMarz دارای لایه DNS Guard برای کنترل مسیر DNS queryها است.

در configuration مربوط به xray-core می‌توان DNS outbound و routing ruleهای مربوط به DNS را برای جلوگیری از عبور DNS از مسیر کنترل‌نشده ایجاد کرد.

در محیط‌هایی که implementation پروژه از DNS-over-HTTPS استفاده می‌کند، DNS queryها می‌توانند از مسیر تونل مدیریت‌شده عبور داده شوند. رفتار دقیق باید از configuration و implementation فعلی استخراج شود.

هدف این بخش جلوگیری از نشت DNS خارج از مسیر موردنظر orchestration است.

### 🔒 Kill Switch

Kill Switch برای جلوگیری از عبور traffic خارج از مسیر proxy در شرایطی که مسیر موردنظر فعال یا سالم نیست طراحی شده است.

نمونه commandهای مدیریتی:

```bash
bimarz killswitch --help
bimarz killswitch enable
bimarz killswitch disable
bimarz killswitch status
```

در صورت پشتیبانی نسخه فعلی CLI از تعیین UID مربوط به xray، می‌توان آن را مطابق help همان نسخه مشخص کرد.

در محیط‌هایی مانند Termux، proot یا محیط‌هایی که دسترسی کامل kernel و root ندارند، Kill Switch ممکن است به software fallback محدود شود. بنابراین README نباید وجود kernel-level enforcement را در تمام محیط‌ها تضمین کند.

### 🖥️ رابط گرافیکی

BiMarz دارای GUI مبتنی بر PySide6 است.

GUI برای عملیات مدیریتی orchestrator طراحی شده و منطق business نباید به‌صورت جداگانه در GUI تکرار شود.

بسته به implementation فعلی، GUI می‌تواند شامل مدیریت profile، وضعیت اتصال و کنترل عملیات اصلی orchestrator باشد. جزئیات دقیق قابلیت‌های GUI باید از کد فعلی GUI و release مربوطه استخراج شود.

### 🧪 تست‌ها

پروژه دارای چند سطح تست است:

- Python unit tests
- Python integration tests
- Rust unit tests
- parser tests
- xray configuration tests
- VLESS/Reality builder tests
- engine/xray-core integration tests

اجرای تست‌های Python:

```bash
pytest
```

اجرای تست‌های Rust:

```bash
cargo test --manifest-path engine-core/Cargo.toml
```

### 🧹 بررسی کیفیت کد

```bash
ruff check .
ruff format --check .
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
```

این بررسی‌ها باید قبل از اعلام یک تغییر به‌عنوان نسخه سالم یا release-ready اجرا شوند.

### 🔐 Security

امنیت پروژه بر پایه جداسازی مسئولیت‌ها، validation ورودی‌ها و کنترل دقیق boundaryهای Python/Rust طراحی شده است.

- Python مسئول orchestration است.
- Rust مسئول engine و عملیات سطح پایین است.
- ورودی‌ها پیش از ساخت protobuf اعتبارسنجی می‌شوند.
- ورودی خام کاربر نباید به‌عنوان command سیستم‌عامل اجرا شود.
- خطاها باید به شکل ساختاریافته مدیریت شوند.
- API contractها باید تست شوند.
- credentialها و داده‌های حساس نباید در repository قرار بگیرند.
- Reality private key نباید در repository، log یا فایل عمومی ذخیره یا منتشر شود.

### 🔎 Security Audits

pipeline امنیتی پروژه شامل بررسی dependencyها و کد با ابزارهای زیر است:

- `cargo-audit` برای dependencyهای Rust
- `pip-audit` برای dependencyهای Python
- `bandit` برای بررسی الگوهای امنیتی Python

در سابقه Phase 6، دو advisory شناخته‌شده مربوط به PyO3 یعنی `RUSTSEC-2025-0020` و `RUSTSEC-2026-0177` مستند شده‌اند.

این موارد در `SECURITY.md` با disposition مربوطه ثبت شده‌اند. وجود advisory در dependency به‌تنهایی به معنی استفاده BiMarz از API آسیب‌دیده نیست و وضعیت واقعی باید از مستندات security project و dependency tree بررسی شود.

PyO3 به نسخه 0.29.2 ارتقا یافته و این migration در چارچوب Phase 6 با build، تست، lint، بسته‌بندی و audit اعتبارسنجی شده است.

### 🤖 قوانین توسعه

قبل از هر تغییر در repository، توسعه‌دهندگان و AI agentها باید اسناد زیر را مطالعه کنند:

```text
SECURITY.md
```

این اسناد مرجع اصلی قوانین پروژه برای موارد زیر هستند:

- معماری
- مرز Python/Rust
- قراردادهای PyO3
- تست‌ها
- lint و formatting
- امنیت
- مدیریت dependencyها
- فرآیند توسعه
- قوانین تغییر repository

README جایگزین این اسناد نیست و در صورت وجود تعارض، قوانین repository و اسناد الزام‌آور پروژه مرجع هستند.

### 📋 Source of Truth

برای اطلاعاتی که ممکن است با تغییر کد تغییر کنند، منابع زیر مرجع اصلی هستند:

1. `pyproject.toml` برای metadata و Python packaging
2. `Cargo.toml` برای Rust crate و dependencyهای Rust
3. CLI implementation برای commandها و optionها
5. `SECURITY.md` برای یافته‌های امنیتی و disposition
6. `LICENSE` برای مجوز پروژه
7. CI workflows برای pipelineهای build و test
8. implementation واقعی برای رفتار runtime

README باید هنگام تغییر این منابع بررسی و در صورت نیاز به‌روزرسانی شود.

### 📦 نسخه پروژه

نسخه پروژه باید از metadata رسمی repository پیروی کند.

```text
BiMarz 0.2.3
```

این مقدار باید هنگام release با version واقعی package و engine تطبیق داده شود.

### 🖥️ پلتفرم‌های پشتیبانی‌شده

پشتیبانی واقعی platform به implementation و سطح دسترسی محیط بستگی دارد.

| محیط | تشخیص | Kill Switch | وضعیت |
|---|---|---|---|
| Arch Linux / desktop Linux | خودکار یا platform-specific | وابسته به privilege | پشتیبانی‌شده در محیط مناسب |
| Kali NetHunter + Termux | platform-aware | ممکن است software fallback باشد | وابسته به محیط |
| Termux | platform-aware | محدود به capability محیط | وابسته به محیط |
| WSL | environment-dependent | وابسته به privilege و network stack | وابسته به محیط |
| سایر Linuxها | generic detection | وابسته به محیط | implementation-dependent |

> نباید قابلیت kernel-level Kill Switch در محیطی که root یا دسترسی لازم به kernel ندارد تضمین شود.

### 📜 CHANGELOG

تغییرات مهم فنی، تصمیمات معماری و bug fixهای مهم پروژه در `CHANGELOG.md` ثبت می‌شوند.

README نمای کلی پروژه را ارائه می‌کند و `CHANGELOG.md` برای تاریخچه تغییرات implementation و releaseها مرجع مناسب‌تری است.

### 🗑️ حذف نصب

اگر پروژه داخل virtual environment نصب شده است:

```bash
deactivate
rm -rf .venv
```

برای حذف package نصب‌شده به‌صورت editable:

```bash
python -m pip uninstall bimarz
```

برای حذف داده‌های کاربر، در صورتی که این مسیر توسط نسخه فعلی استفاده شود:

```bash
rm -rf ~/.config/bimarz
```

برای حذف repository محلی:

```bash
cd ..
rm -rf bimarz
```

> حذف repository و `.venv` باعث حذف source code و محیط توسعه محلی می‌شود. حذف `~/.config/bimarz` نیز ممکن است profileها، credentialهای رمزنگاری‌شده و logهای محلی را حذف کند. قبل از اجرای `rm -rf` مسیر و داده‌های موردنیاز را بررسی کنید.

### 🤝 مشارکت

Issue و Pull Request برای توسعه پروژه قابل استفاده هستند. قبل از ارسال تغییر، بررسی‌های کیفیت و تست‌های repository را اجرا کنید.

```bash
ruff check .
ruff format --check .
pytest
cargo fmt --check
cargo test --manifest-path engine-core/Cargo.toml
cargo clippy --all-targets --all-features -- -D warnings
```


### 📜 مجوز

مجوز رسمی پروژه در فایل `LICENSE` repository تعریف شده است. `LICENSE` منبع اصلی برای متن و شرایط حقوقی مجوز است.

### 👨‍💻 توسعه‌دهنده

GitHub: `msoleimani62`

---

## 🇬🇧 English

### 📖 Overview

BiMarz is a cross-platform orchestration layer around xray-core for managing VLESS + Reality + XTLS Vision connections.

The project separates high-level orchestration from low-level engine functionality by using Python for orchestration and Rust for the engine layer.

Python handles profiles, subscriptions, health monitoring, failover, DNS-related orchestration, CLI and GUI operations, while Rust handles the engine layer and low-level functionality through a PyO3 boundary.

### ✨ Features

- VLESS support
- Reality support
- XTLS Vision support
- VLESS share-link parsing
- VLESS and Reality parameter extraction
- xray-core outbound generation
- gRPC communication with xray-core
- Health checks
- Failover
- Server profile management
- Subscription management where implemented
- Secure profile storage where implemented
- DNS leak protection
- Kill switch
- Command-line interface
- PySide6 graphical interface
- Rust engine through PyO3
- Python and Rust tests
- Unit and integration testing
- Linting and formatting
- CI/CD and release-related workflows
- Dependency security auditing with cargo-audit, pip-audit and bandit

### 🏗️ Architecture

```text
                         ┌────────────────────────────┐
                         │         BiMarz CLI         │
                         └──────────────┬─────────────┘
                                        │
                         ┌──────────────▼─────────────┐
                         │     Python Orchestrator    │
                         │                            │
                         │ profiles                   │
                         │ subscriptions              │
                         │ health / failover          │
                         │ DNS / kill switch          │
                         │ CLI / GUI                  │
                         └──────────────┬─────────────┘
                                        │ PyO3
                         ┌──────────────▼─────────────┐
                         │        Rust Engine         │
                         │        engine-core         │
                         └──────────────┬─────────────┘
                                        │ gRPC
                         ┌──────────────▼─────────────┐
                         │          xray-core         │
                         └────────────────────────────┘
```

Python owns orchestration and high-level logic. Rust owns the engine and low-level operations. This boundary keeps orchestration concerns separate from engine functionality and avoids duplicating business logic between CLI and GUI.

### 📁 Project Structure

```text
bimarz/
├── orchestrator/
│   └── bimarz/
│       ├── cli/
│       ├── gui/
│       ├── parsers/
│       ├── services/
│       ├── models/
│       ├── dns_leak_guard.py
│       ├── xray_config.py
│       └── ...
├── engine-core/
│   └── src/
│       ├── vless_builder.rs
│       ├── grpc_client.rs
│       └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── ...
├── proto/
├── .github/
│   └── workflows/
├── pyproject.toml
├── Cargo.toml
├── SECURITY.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

The structure above is a high-level repository overview. The actual repository and its source-of-truth files remain authoritative for exact file layout and implementation details.

### 🗺️ Roadmap

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Initial skeleton, build system and proto fetch |
| 1 | ✅ Complete | Rust engine-core, gRPC client and VLESS builder |
| 2 | ✅ Complete | Profile & Subscription Manager and encrypted storage |
| 3 | ✅ Complete | Connection orchestration, health check and failover |
| 4 | ✅ Complete | Kill switch, DNS leak protection and platform detection |
| 5 | ✅ Complete | Final CLI, GUI skeleton, packaging and release workflow |
| 6 | ✅ Complete | CI/CD, security audit, quality gates and docs/INSTALL.md |
| 7 | ✅ Complete | Subscription URL parsing, base64 decoding and auto-update profiles |
| 8 | ✅ Complete | Connection lifecycle hardening, transactional rollback, cleanup observability and acceptance validation |
| 9 | 🚧 Started | Android app (Kotlin + Jetpack Compose + uniffi-rs). Initial scaffold only — not yet built/tested on a real device. Details: [`android/README.md`](android/README.md) |

> Roadmap entries must reflect verified implementation status. Planned functionality must not be documented as currently available.

### ⚙️ Requirements

| Tool | Requirement | Notes |
|---|---|---|
| Python | 3.12+ | orchestration runtime |
| Rust | stable toolchain | engine-core build |
| Cargo | stable | Rust build and tests |
| maturin | compatible with pyproject.toml | PyO3 bridge build |
| xray-core | project-compatible configuration | external runtime engine |
| Git | compatible system version | repository management |

Exact dependency versions must be verified against `pyproject.toml`, `Cargo.toml` and the repository configuration rather than being inferred from this README.

### 🛰️ xray-core

BiMarz requires xray-core for actual connection operation. BiMarz does not silently install xray-core. Installation and version selection should follow the current project configuration and the target operating system.

After installation, run:

```bash
bimarz doctor
```

### 📦 Installation from Source

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install maturin
maturin develop --release
```

If the current repository requires additional proto files or external build inputs, follow the procedures defined by the current project configuration and documentation.

### 🔨 Build the Rust Extension

```bash
maturin develop --release
```

This builds the Rust/PyO3 extension for the development environment.

### 🩺 Installation Check

```bash
bimarz doctor
bimarz doctor --help
```

Use `doctor` as the primary environment diagnostic when supported by the installed implementation.

### 👤 Profile Management

BiMarz manages connection information through server profiles.

```bash
bimarz profile --help
bimarz profile list
bimarz profile add "vless://..."
bimarz profile remove <id>
```

The installed CLI remains authoritative for exact arguments and options.

### 🔐 Profile Encryption

Where encrypted profile storage is enabled by the current implementation, profile data is protected using a **PBKDF2-HMAC-SHA256** and **Fernet** based encryption chain.

For scripting and CI, if supported by the current implementation, the profile password can be supplied through:

```bash
export BIMARZ_PROFILE_PASSWORD="..."
```

Never commit passwords, UUIDs, Reality private keys or other real credentials.

### 🔗 VLESS Share Links

BiMarz can parse VLESS share links and extract supported parameters such as UUID, server address, port, flow, security, SNI, fingerprint, Reality public key, short ID, transport settings and other supported fields.

Example:

```text
vless://UUID@example.com:443?type=tcp&security=reality&sni=example.com&fp=chrome&pbk=PUBLIC_KEY&sid=SHORT_ID&flow=xtls-rprx-vision#My-Server
```

The values above are placeholders and are not real credentials.

### 🚀 Connect

```bash
bimarz connect --help
bimarz connect <id>
bimarz connect <id> --auto-failover
bimarz connect <id> --killswitch
bimarz connect <id> --auto-failover --killswitch
```

BiMarz prepares the required xray-core configuration and manages the active outbound during connection operations.

The installed CLI must be used to verify the exact profile-selection mechanism and supported options.

### ❤️ Health Check

```bash
bimarz healthcheck --help
bimarz healthcheck
```

Health checks monitor managed endpoints and connection health. The current implementation may execute checks concurrently across managed profiles.

### 🔄 Failover

BiMarz can monitor managed endpoints and switch away from an unavailable active route when the configured failover conditions are met.

```bash
bimarz connect <id> --auto-failover
```

Exact thresholds, policies and switching conditions depend on the current implementation.

### 🛡️ DNS Leak Protection

BiMarz provides a DNS Guard layer intended to control DNS query routing.

The xray-core configuration may include DNS outbounds and routing rules so DNS queries do not escape through an uncontrolled path.

Where the current implementation uses DNS-over-HTTPS, DNS traffic can be routed through the managed tunnel. Exact behavior must be verified against the current configuration and implementation.

### 🔒 Kill Switch

The kill switch is designed to prevent traffic from bypassing the intended proxy path when the managed route is unavailable or inactive.

```bash
bimarz killswitch --help
bimarz killswitch enable
bimarz killswitch disable
bimarz killswitch status
```

Where supported by the installed CLI, an xray UID can be provided according to the command help.

Actual kernel-level behavior depends on the operating system, privileges and network environment. Termux, proot and similar restricted environments may require a software fallback.

### 🖥️ Graphical Interface

BiMarz includes a PySide6-based GUI for orchestrator operations.

The GUI should remain a presentation and control layer and should not duplicate business logic implemented by the orchestrator services.

The exact GUI feature set must be verified against the current GUI implementation.

### 🧪 Testing

The project contains multiple testing layers:

- Python unit tests
- Python integration tests
- Rust unit tests
- parser tests
- xray configuration tests
- VLESS/Reality builder tests
- engine/xray-core integration tests

Python tests:

```bash
pytest
```

Rust tests:

```bash
cargo test --manifest-path engine-core/Cargo.toml
```

### 🧹 Code Quality

```bash
ruff check .
ruff format --check .
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
```

These checks should pass before a change is considered release-ready.

### 🔐 Security

The security model is based on separation of responsibilities, strict input validation and explicit Python/Rust boundaries.

- Python owns orchestration.
- Rust owns the engine layer.
- Inputs are validated before protobuf construction.
- Raw user input must never be executed as an operating-system command.
- Errors should be handled through structured error paths.
- API contracts should be covered by tests.
- Credentials and sensitive data must not be committed to the repository.
- Reality private keys must never be stored in the repository, logs or public files.

### 🔎 Security Auditing

Security checks include:

- `cargo-audit` for Rust dependency advisories
- `pip-audit` for Python dependency advisories
- `bandit` for Python security checks

Phase 6 recorded two known PyO3 advisories: `RUSTSEC-2025-0020` and `RUSTSEC-2026-0177`.

These findings are documented in `SECURITY.md` with their current disposition. An advisory in a dependency does not by itself prove that the affected API is used by BiMarz; the dependency tree and security documentation remain authoritative.

PyO3 has been upgraded to 0.29.2 as part of the Phase 6 security migration.

### 🤖 Development Rules

Before modifying the repository, developers and AI agents must read:

```text
SECURITY.md
```

These documents define project rules for architecture, Python/Rust boundaries, PyO3 contracts, testing, linting, security, dependency management and development workflow.

The README does not replace these documents. If a conflict exists, the repository constitution and binding development rules take precedence.

### 📋 Source of Truth

The following sources are authoritative for information that changes with implementation:

1. `pyproject.toml` for Python metadata and packaging
2. `Cargo.toml` for Rust package configuration and dependencies
3. CLI implementation for commands and options
5. `SECURITY.md` for security findings and disposition
6. `LICENSE` for licensing terms
7. CI workflows for build and test pipelines
8. Runtime implementation for actual behavior

The README should be reviewed whenever these sources change.

### 📦 Current Version

The project version must follow the repository metadata and its defined source of truth.

```text
BiMarz 0.2.3
```

This value must be verified against the actual package and engine versions when preparing a release.

### 🖥️ Supported Platforms

Actual platform support depends on the implementation and privileges available in the target environment.

| Environment | Detection | Kill Switch | Status |
|---|---|---|---|
| Arch Linux / desktop Linux | automatic or platform-specific | privilege-dependent | supported in suitable environments |
| Kali NetHunter + Termux | platform-aware | may use software fallback | environment-dependent |
| Termux | platform-aware | limited by environment capabilities | environment-dependent |
| WSL | environment-dependent | privilege and network-stack dependent | environment-dependent |
| Other Linux distributions | generic detection | environment-dependent | implementation-dependent |

> Kernel-level kill-switch behavior must not be assumed in environments without the required root and kernel capabilities.

### 📜 CHANGELOG

Important technical changes, architectural decisions and significant bug fixes are recorded in `CHANGELOG.md`.

The README provides the current project overview, while `CHANGELOG.md` is the appropriate reference for implementation and release history.

### 🗑️ Uninstallation

For a local virtual environment:

```bash
deactivate
rm -rf .venv
```

For an editable package installation:

```bash
python -m pip uninstall bimarz
```

For user data, when this path is used by the current implementation:

```bash
rm -rf ~/.config/bimarz
```

To remove the local repository:

```bash
cd ..
rm -rf bimarz
```

> Removing `~/.config/bimarz` may delete local profiles, encrypted credentials and logs. Verify the path before running `rm -rf`.

### 🤝 Contributing

Issues and Pull Requests are welcome. Before submitting a change, run the repository quality checks and tests.

```bash
ruff check .
ruff format --check .
pytest
cargo fmt --check
cargo test --manifest-path engine-core/Cargo.toml
cargo clippy --all-targets --all-features -- -D warnings
```


### 📜 License

The official project license is defined by the `LICENSE` file in the repository. The `LICENSE` file is the authoritative source for the exact license terms.

### 👨‍💻 Developer

GitHub: `msoleimani62`

---

### 📌 Documentation Policy

README content must describe the implementation that actually exists in the repository. Features, commands, versions, dependencies and architecture must not be documented as available merely because they are planned.

When implementation and documentation diverge, the implementation must be reviewed first and the README must then be updated to match verified behavior.

### 📎 Quick Reference

```text
Project       : BiMarz
Architecture  : Python + Rust + PyO3
Core          : xray-core
Protocols     : VLESS / Reality / XTLS Vision
GUI           : PySide6
Build         : maturin
Python        : 3.12+
Rust          : stable toolchain
License       : See LICENSE
GitHub        : msoleimani62
```

### 🔗 Useful Repository Documents

- `SECURITY.md` — security findings, advisories and dispositions
- `CHANGELOG.md` — technical and release history
- `docs/INSTALL.md` — detailed installation documentation
- `LICENSE` — authoritative license terms
