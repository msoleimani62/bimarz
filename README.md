# 🐉 BiMarz — Cross-Platform Xray/VLESS Reality Orchestrator

**BiMarz (بی‌مرز)** یک orchestrator چندسکویی برای مدیریت اتصال‌های **Xray/VLESS + Reality + XTLS Vision** است که با معماری ترکیبی **Python + Rust** طراحی شده است.

BiMarz لایه orchestration سطح بالا را در Python نگه می‌دارد و قابلیت‌های engine و عملیات سطح پایین را در Rust پیاده‌سازی می‌کند. این معماری با هدف ایجاد یک سیستم قابل‌اعتماد، تست‌پذیر، امن و قابل توسعه برای مدیریت پروفایل‌ها، اتصال‌ها، health monitoring، failover، DNS leak protection و kill switch طراحی شده است.

---

## 🇮🇷 فارسی

### 📖 معرفی

BiMarz یک ابزار مدیریت و orchestration برای **xray-core** است که مسئولیت‌ها را میان دو لایه اصلی تقسیم می‌کند:

- **Python**: orchestration، مدیریت profile، health check، failover، DNS، CLI و GUI
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
- DNS Leak Protection
- Kill Switch
- CLI
- رابط گرافیکی مبتنی بر PySide6
- Rust engine با PyO3
- تست‌های Python و Rust
- تست‌های unit و integration
- lint و formatting
- CI و workflowهای مرتبط با کیفیت و release

### 🏗️ معماری

```text
                         ┌──────────────────────┐
                         │      BiMarz CLI      │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ Python Orchestrator  │
                         │                      │
                         │ profiles             │
                         │ health               │
                         │ failover             │
                         │ DNS                  │
                         │ CLI / GUI            │
                         └──────────┬───────────┘
                                    │ PyO3
                         ┌──────────▼───────────┐
                         │     Rust Engine      │
                         │     engine-core      │
                         └──────────┬───────────┘
                                    │ gRPC
                         ┌──────────▼───────────┐
                         │      xray-core       │
                         └──────────────────────┘
```

**Python مسئول orchestration و منطق سطح بالا است و Rust مسئول engine و عملیات سطح پایین است.**

### 📁 ساختار پروژه

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
├── AGENTS.md
├── AI_AGENT_RULES.md
├── LICENSE
└── README.md
```

> ساختار بالا نمای کلی repository است. برای جزئیات دقیق هر نسخه، ساختار واقعی فایل‌های repository مرجع اصلی است.

### ⚙️ پیش‌نیازها

- Python 3.12 یا جدیدتر
- Rust و Cargo
- maturin
- xray-core
- Git

#### xray-core

BiMarz برای اجرای واقعی اتصال‌ها به **xray-core** نیاز دارد. README نصب خودکار یا نسخه خاصی از xray-core را فرض نمی‌کند؛ نسخه و روش نصب باید مطابق configuration و مستندات فعلی پروژه و سیستم‌عامل مقصد انتخاب شود.

پس از نصب، دستور زیر برای بررسی وضعیت محیط استفاده می‌شود:

```bash
bimarz doctor
```

در صورتی که `doctor` وضعیت xray-core یا executable مربوط به آن را گزارش کند، خروجی آن مرجع اصلی تشخیص محیط اجرایی خواهد بود.

### 📦 نصب از سورس

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install maturin
python -m pip install -e .
```

### 🔨 ساخت Rust Extension

برای build کردن extension مربوط به Rust:

```bash
maturin develop --release
```

در پروژه‌هایی که build backend مربوط به maturin است، روش build نهایی باید مطابق `pyproject.toml` فعلی repository انجام شود.

### 🩺 بررسی سلامت نصب

پس از نصب:

```bash
bimarz doctor
```

این دستور برای بررسی وضعیت محیط، وابستگی‌ها و اجزای اصلی نصب‌شده استفاده می‌شود.

### 👤 مدیریت Profile

BiMarz اطلاعات اتصال را در قالب server profile مدیریت می‌کند.

دستورهای اصلی CLI شامل موارد زیر هستند:

```bash
bimarz profile --help
bimarz profile list
bimarz profile add
bimarz profile remove
```

جزئیات argumentها و optionهای هر command را همیشه می‌توان با `--help` مشاهده کرد.

### 🔗 VLESS Share Link

BiMarz می‌تواند VLESS share link را parse کرده و پارامترهای پشتیبانی‌شده را استخراج کند.

اطلاعات قابل استخراج می‌تواند شامل موارد زیر باشد:

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

> مقادیر موجود در این نمونه صرفاً placeholder هستند و نباید به عنوان credential واقعی استفاده شوند.

### 🚀 اتصال

برای مشاهده گزینه‌های اتصال:

```bash
bimarz connect --help
```

BiMarz هنگام اتصال، configuration موردنیاز xray-core را آماده کرده و outbound فعال را مدیریت می‌کند.

نحوه انتخاب profile فعال و سایر argumentها باید از خروجی `bimarz connect --help` در نسخه نصب‌شده مشخص شود.

### ❤️ Health Check

```bash
bimarz healthcheck --help
```

Health Check برای بررسی وضعیت endpointها و سلامت مسیرهای مدیریت‌شده استفاده می‌شود.

### 🔄 Failover

در صورت از دسترس خارج شدن مسیر فعال، سیستم failover می‌تواند وضعیت مسیرهای مدیریت‌شده را بررسی کرده و بر اساس سیاست‌های پروژه مسیر مناسب بعدی را انتخاب کند.

جزئیات thresholdها، policyها و شرایط تغییر مسیر باید مطابق implementation فعلی پروژه بررسی شود.

### 🛡️ DNS Leak Protection

BiMarz دارای لایه DNS Guard برای کنترل مسیر DNS queryها است.

در configuration مربوط به xray-core می‌توان DNS outbound و routing ruleهای مربوط به DNS را برای جلوگیری از عبور DNS از مسیر کنترل‌نشده ایجاد کرد.

هدف این بخش جلوگیری از نشت DNS خارج از مسیر موردنظر orchestration است.

### 🔒 Kill Switch

```bash
bimarz killswitch --help
```

Kill Switch برای جلوگیری از عبور traffic خارج از مسیر proxy در شرایطی که مسیر موردنظر فعال یا سالم نیست طراحی شده است.

فعال‌سازی واقعی Kill Switch به قابلیت‌های سیستم‌عامل، سطح دسترسی و implementation فعلی BiMarz وابسته است.

### 🖥️ رابط گرافیکی

BiMarz دارای GUI مبتنی بر **PySide6** است.

رابط گرافیکی برای عملیات اصلی مدیریت orchestrator طراحی شده و بسته به وضعیت implementation می‌تواند شامل مدیریت profile، وضعیت اتصال و کنترل عملیات اصلی باشد.

جزئیات دقیق قابلیت‌های GUI باید از نسخه فعلی کد GUI و release مربوطه استخراج شود.

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

برای بررسی lint و formatting:

```bash
ruff check .
ruff format --check .
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
```

تمام این بررسی‌ها باید قبل از اعلام یک تغییر به عنوان نسخه سالم یا release-ready اجرا شوند.

### 🔬 VLESS Builder

Rust engine دارای builder اختصاصی برای تبدیل پارامترهای VLESS + Reality + Vision به ساختارهای protobuf موردنیاز xray-core است.

این بخش مسئولیت‌هایی مانند موارد زیر را بر عهده دارد:

- VLESS Account
- VLESS Outbound Config
- Reality Config
- Stream Config
- Sender Config
- Server Endpoint
- IPv4 address
- IPv6 address
- Domain address
- Reality public key decoding
- Reality short ID decoding
- UUID validation
- address validation
- port validation

ورودی‌ها باید پیش از ساخت protobuf اعتبارسنجی شوند تا داده نامعتبر وارد لایه engine نشود.

### 🔌 xray-core Configuration

BiMarz configuration موردنیاز xray-core را بر اساس نیازهای orchestration ایجاد یا مدیریت می‌کند.

اجزای مورد استفاده می‌توانند شامل موارد زیر باشند:

- API
- HandlerService
- StatsService
- SOCKS inbound
- outbound configuration
- active outbound routing
- statistics
- DNS configuration
- routing rules

Configuration واقعی باید همیشه با implementation فعلی پروژه تطبیق داده شود.

### 📊 Statistics

برای health monitoring و مشاهده وضعیت اتصال، BiMarz از قابلیت‌های statistics و StatsService مربوط به xray-core استفاده می‌کند.

این اطلاعات می‌تواند برای health monitoring، تشخیص وضعیت endpoint و تصمیم‌گیری در failover مورد استفاده قرار گیرد.

### 🔐 امنیت

امنیت پروژه بر پایه جداسازی مسئولیت‌ها و validation ورودی‌ها طراحی شده است.

- Python مسئول orchestration است.
- Rust مسئول engine و عملیات سطح پایین است.
- ورودی‌ها پیش از ساخت protobuf اعتبارسنجی می‌شوند.
- ورودی خام کاربر نباید به عنوان command سیستم‌عامل اجرا شود.
- خطاها باید به شکل ساختاریافته مدیریت شوند.
- API contractها باید تست شوند.
- credentialها و داده‌های حساس نباید در repository قرار بگیرند.
- Reality private key نباید در repository، log یا فایل عمومی ذخیره یا منتشر شود.

### 🤖 قوانین توسعه

قبل از هر تغییر در repository، توسعه‌دهندگان و AI agentها باید اسناد زیر را مطالعه کنند:

```text
AGENTS.md
AI_AGENT_RULES.md
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

برای اطلاعاتی که ممکن است با تغییر کد تغییر کنند، منبع اصلی repository است:

1. `pyproject.toml` برای metadata و Python packaging
2. `Cargo.toml` برای Rust crate و dependencyهای Rust
3. CLI implementation برای commandها و optionها
4. `AGENTS.md` و `AI_AGENT_RULES.md` برای قوانین توسعه
5. `LICENSE` برای مجوز پروژه
6. CI workflows برای pipelineهای build و test

README باید هنگام تغییر این منابع به‌روزرسانی شود.

### 📦 نسخه پروژه

نسخه باید از metadata رسمی پروژه و source of truth تعریف‌شده در repository پیروی کند.

```text
BiMarz 0.2.0
```

این مقدار باید هنگام release با version واقعی package و engine تطبیق داده شود.

### 🗑️ حذف نصب

اگر پروژه داخل virtual environment نصب شده است:

```bash
deactivate
rm -rf .venv
```

برای حذف package نصب‌شده به صورت editable:

```bash
python -m pip uninstall bimarz
```

در صورت نیاز می‌توان repository محلی را نیز حذف کرد:

```bash
cd ..
rm -rf bimarz
```

> حذف repository باعث حذف source code محلی می‌شود. قبل از اجرای `rm -rf` از مسیر فعلی اطمینان حاصل کنید.

### 📜 مجوز

مجوز رسمی پروژه در فایل `LICENSE` repository تعریف شده است.

همیشه متن و نوع مجوز موجود در `LICENSE` را مرجع اصلی بدانید و از فرض کردن نوع license بر اساس README خودداری کنید.

### 👨‍💻 توسعه‌دهنده

GitHub: `msoleimani62`

---

## 🇬🇧 English

### 📖 Overview

BiMarz is a cross-platform orchestration layer around **xray-core** for managing **VLESS + Reality + XTLS Vision** connections.

The project separates high-level orchestration from low-level engine functionality by using **Python** for orchestration and **Rust** for the engine layer.

Python handles profiles, health monitoring, failover, DNS-related orchestration, CLI and GUI operations, while Rust handles the engine layer and low-level functionality through a PyO3 boundary.

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
- DNS leak protection
- Kill switch
- Command-line interface
- PySide6 graphical interface
- Rust engine through PyO3
- Python and Rust tests
- Unit and integration testing
- Linting and formatting
- CI and release-related workflows

### 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │      BiMarz CLI      │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ Python Orchestrator  │
                         │                      │
                         │ profiles             │
                         │ health               │
                         │ failover             │
                         │ DNS                  │
                         │ CLI / GUI            │
                         └──────────┬───────────┘
                                    │ PyO3
                         ┌──────────▼───────────┐
                         │     Rust Engine      │
                         │     engine-core      │
                         └──────────┬───────────┘
                                    │ gRPC
                         ┌──────────▼───────────┐
                         │      xray-core       │
                         └──────────────────────┘
```

Python owns orchestration and high-level logic. Rust owns the engine and low-level operations.

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
├── AGENTS.md
├── AI_AGENT_RULES.md
├── LICENSE
└── README.md
```

The repository structure above is a high-level overview. The actual repository remains the authoritative source for the exact file layout.

### ⚙️ Requirements

- Python 3.12 or newer
- Rust and Cargo
- maturin
- xray-core
- Git

#### xray-core

BiMarz requires **xray-core** for actual connection operation. This README does not assume a specific installation method or silently install xray-core. The required version and installation method should follow the current project configuration and the target operating system.

After installation, run:

```bash
bimarz doctor
```

The doctor command should be used as the primary environment check when supported by the current implementation.

### 📦 Installation from Source

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install maturin
python -m pip install -e .
```

### 🔨 Build the Rust Extension

```bash
maturin develop --release
```

The final build procedure should always follow the current `pyproject.toml` and maturin configuration.

### 🩺 Installation Check

```bash
bimarz doctor
```

Use this command to inspect the local environment, dependencies and available project components.

### 👤 Profile Management

BiMarz manages connection information through server profiles.

```bash
bimarz profile --help
bimarz profile list
bimarz profile add
bimarz profile remove
```

Command-specific arguments and options should always be verified with the installed CLI using `--help`.

### 🔗 VLESS Share Links

BiMarz can parse VLESS share links and extract supported parameters such as UUID, server address, port, flow, security, SNI, fingerprint, Reality public key, short ID, transport settings and other supported fields.

Example:

```text
vless://UUID@example.com:443?type=tcp&security=reality&sni=example.com&fp=chrome&pbk=PUBLIC_KEY&sid=SHORT_ID&flow=xtls-rprx-vision#My-Server
```

The values in this example are placeholders and are not real credentials.

### 🚀 Connect

```bash
bimarz connect --help
```

BiMarz prepares the required xray-core configuration and manages the active outbound during connection operations.

The exact profile-selection mechanism and command arguments must be obtained from the installed version using `bimarz connect --help`.

### ❤️ Health Check

```bash
bimarz healthcheck --help
```

Health checks are used to monitor managed endpoints and connection health.

### 🔄 Failover

BiMarz can monitor managed endpoints and switch away from an unavailable active route when the configured failover conditions are met.

The exact thresholds, policies and switching conditions depend on the current implementation.

### 🛡️ DNS Leak Protection

BiMarz provides a DNS Guard layer intended to control DNS query routing.

The xray-core configuration may include DNS outbounds and routing rules for DNS traffic so that DNS queries do not escape through an uncontrolled path.

### 🔒 Kill Switch

```bash
bimarz killswitch --help
```

The kill switch is designed to prevent traffic from bypassing the intended proxy path when the managed route is unavailable or inactive.

Actual kill-switch behavior depends on the operating system, required privileges and the current implementation.

### 🖥️ Graphical Interface

BiMarz includes a **PySide6-based GUI** for core orchestrator operations.

Depending on the current implementation, the GUI may provide profile management, connection status and control over core orchestration operations.

The current GUI implementation remains the authoritative source for its exact feature set.

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

### 🔬 VLESS Builder

The Rust engine contains a dedicated builder for converting VLESS + Reality + Vision parameters into protobuf structures required by xray-core.

It handles VLESS accounts, outbound configuration, Reality configuration, stream settings, sender settings, server endpoints, IPv4/IPv6/domain addresses, Reality key decoding, short-ID decoding and input validation.

Invalid inputs should be rejected before protobuf construction.

### 🔌 xray-core Configuration

BiMarz manages the xray-core configuration required by its orchestration layer.

Depending on the current implementation, this can include:

- API
- HandlerService
- StatsService
- SOCKS inbound
- outbound configuration
- active outbound routing
- statistics
- DNS configuration
- routing rules

The implementation in the repository is the authoritative source for the exact generated configuration.

### 📊 Statistics

BiMarz uses xray-core statistics and StatsService capabilities for connection monitoring and health-related decisions.

Statistics may be used by health monitoring and failover logic to evaluate endpoint state.

### 🔐 Security

The security model is based on separation of responsibilities and strict input validation.

- Python owns orchestration.
- Rust owns the engine layer.
- Inputs are validated before protobuf construction.
- Raw user input must never be executed as an operating-system command.
- Errors should be handled through structured error paths.
- API contracts should be covered by tests.
- Credentials and sensitive data must not be committed to the repository.
- Reality private keys must never be stored in the repository, logs or public files.

### 🤖 Development Rules

Before modifying the repository, developers and AI agents must read:

```text
AGENTS.md
AI_AGENT_RULES.md
```

These documents define the project rules for architecture, Python/Rust boundaries, PyO3 contracts, testing, linting, security, dependencies and development workflow.

The README does not replace these documents. If a conflict exists, the repository constitution and binding development rules take precedence.

### 📋 Source of Truth

The following files are authoritative for information that changes with the implementation:

1. `pyproject.toml` for Python metadata and packaging
2. `Cargo.toml` for Rust package configuration and dependencies
3. CLI implementation for commands and options
4. `AGENTS.md` and `AI_AGENT_RULES.md` for development rules
5. `LICENSE` for the project license
6. CI workflows for build and test pipelines

The README should be updated whenever these sources change.

### 📦 Current Version

The project version must follow the repository metadata and its defined source of truth.

```text
BiMarz 0.2.0
```

This value must be verified against the actual package and engine versions when preparing a release.

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

If the local repository is no longer needed:

```bash
cd ..
rm -rf bimarz
```

Be certain about the current directory before running `rm -rf`.

### 📜 License

The official project license is defined by the `LICENSE` file in the repository.

The `LICENSE` file is the authoritative source for the exact license terms.

### 👨‍💻 Developer

GitHub: `msoleimani62`

---

## 📌 Documentation Policy

README content must describe the implementation that actually exists in the repository. Features, commands, versions, dependencies and architecture must not be documented as available merely because they are planned.

When implementation and documentation diverge, the implementation must be reviewed first and the README must then be updated to match the verified behavior.

---

## 📄 Quick Reference

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
