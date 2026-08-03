# BiMarz (بی‌مرز)

**یک لایه‌ی مدیریتی حرفه‌ای دور باینری Xray-core، ساخته‌شده برای شرایط سخت‌گیرانه‌ی فیلترینگ در ایران (و قابل استفاده در هر جای دنیا).**
**A professional management layer around the Xray-core binary, built for Iran's demanding filtering conditions (and usable anywhere in the world).**

[فارسی](#فارسی) | [English](#english)

> ⚠️ **وضعیت فعلی پروژه:** فازهای **۰ تا ۴ از ۸** نقشه راه کامل و به‌صورت end-to-end روی سخت‌افزار واقعی تایید شده‌اند (نه فقط کامپایل‌شده). جزئیات کامل در بخش «وضعیت و نقشه راه» پایین همین صفحه.
> ⚠️ **Current project status:** phases **0 through 4 of 8** on the roadmap are complete and verified end-to-end on real hardware (not just compiling). Full details in the "Status & Roadmap" section below.

---

## فارسی

### این پروژه چیست؟

`bimarz` قصد ندارد پروتکل رمزنگاری یا مبهم‌سازی بسازد — این کار توسط تیم
[Xray-core](https://github.com/XTLS/xray-core) به بهترین شکل انجام شده و
سال‌ها در میدان واقعی تست شده است. کاری که `bimarz` انجام می‌دهد، ساختن یک
لایه‌ی مدیریتی حرفه‌ای *دور* آن باینری‌ست:

- مدیریت چند پروفایل سرور بدون نیاز به ویرایش دستی فایل JSON
- تست خودکار سلامت سرورها و سوییچ بی‌وقفه به بهترین گزینه (failover)
- Kill-switch سطح سیستم تا در صورت قطع تونل، هیچ ترافیکی لو نرود (با fallback نرم‌افزاری صادقانه در محیط‌هایی مثل Termux/proot که دسترسی کرنل کامل ندارند)
- جلوگیری از نشت DNS با اجبار DNS-over-HTTPS از طریق خودِ تونل
- یک CLI واحد و ساده، با پیام‌های خطای دقیق و قابل‌فهم

### چرا این معماری؟

| لایه | زبان | چرا |
|---|---|---|
| اتصال gRPC به xray-core، health-check موازی، kill-switch، DNS guard | **Rust** | کارایی و ایمنی حافظه برای صدها اتصال همزمان و مدیریت دقیق شبکه |
| CLI، مدیریت پروفایل، پارس subscription، منطق failover | **Python** | سرعت توسعه، خوانایی، تجربه‌ی از قبل اثبات‌شده در پروژه‌ی [open-downloader-cli](https://github.com/msoleimani62/open-downloader-cli) |

معماری فعلی (فاز ۴–۵): CLI ماژولار (`cli.py` ~۱۱۷ خط) با لایه‌های `commands/`، `services/`، `parsers/`، `utils/`؛ پل PyO3 به `engine-core` (Rust)؛ gRPC واقعی به xray-core. جزئیات کامل تصمیمات معماری و باگ‌های واقعی در `CHANGELOG.md` مستند شده‌اند.

### وضعیت و نقشه راه

| فاز | عنوان | وضعیت |
|---|---|---|
| ۰ | اثبات مفهوم gRPC | ✅ کامل |
| ۱ | Engine Adapter (اتصال gRPC واقعی) | ✅ کامل — تایید end-to-end در برابر xray-core زنده |
| ۲ | مدیریت پروفایل و Subscription | ✅ کامل — پارس VLESS+Reality، ذخیره‌ی رمزنگاری‌شده، `bimarz connect` |
| ۳ | Health-check و Failover خودکار | ✅ کامل — `bimarz healthcheck`, `bimarz connect --auto-failover` |
| ۴ | Kill-switch و ضدنشت DNS | ✅ کامل — `bimarz killswitch`, `bimarz connect --killswitch` |
| ۵ | تکمیل CLI و بسته‌بندی | ✅ کامل — doctor لایه‌ای، release workflow، build script |
| ۶ | تست و CI کامل | 🚧 CI پایه آماده (ruff+pytest+cargo)، integration test با xray-core واقعی هنوز نه |
| ۷ | رابط گرافیکی دسکتاپ | ⏳ شروع نشده |
| ۸ | اپ اندروید | ⏳ شروع نشده |

جزئیات فنی هر تغییر در [`CHANGELOG.md`](./CHANGELOG.md) ثبت می‌شود.

### نصب (از سورس — هنوز منتشر نشده)

این پروژه هنوز به‌صورت پکیج آماده منتشر نشده. نصب فعلی فقط برای توسعه است.

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
cat engine-core/proto/README.md
```

بعد از خواندن راهنمای proto (چون فایل‌های proto رسمی xray-core باید جدا واکشی شوند):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
python3 -m venv .venv
source .venv/bin/activate
pip install maturin
maturin develop --release
bimarz doctor
```

### استفاده

```bash
bimarz doctor                          # بررسی کامل محیط، باینری xray-core، وضعیت پروفایل‌ها و kill-switch
bimarz doctor --xray-bin /path/xray    # مسیر صریح باینری xray-core
bimarz --debug doctor                  # نمایش کامل خطای فنی در صورت بروز مشکل

bimarz profile add "vless://..."       # افزودن پروفایل از یک لینک اشتراک VLESS+Reality+Vision
bimarz profile list                    # نمایش پروفایل‌های ذخیره‌شده
bimarz profile remove <id>             # حذف یک پروفایل با شناسه‌اش

bimarz healthcheck                     # تست سلامت موازی همه‌ی پروفایل‌های ذخیره‌شده

bimarz connect <id>                              # اجرای xray-core و اتصال با یک پروفایل (Ctrl+C برای قطع)
bimarz connect <id> --auto-failover              # سوییچ خودکار به بهترین جایگزین در صورت قطعی مکرر
bimarz connect <id> --killswitch                 # جلوگیری از نشت ترافیک در صورت قطع ناگهانی تونل
bimarz connect <id> --auto-failover --killswitch # هر دو با هم

bimarz killswitch enable --xray-uid $(id -u)     # فعال‌سازی دستی kill-switch (خارج از bimarz connect)
bimarz killswitch disable                        # غیرفعال‌سازی
bimarz killswitch status                         # نمایش وضعیت فعلی
```

پروفایل‌ها با یک پسورد رمزنگاری می‌شوند (اولین بار که ذخیره می‌کنی، همون پسورد پرسیده و ثابت می‌شود). برای اسکریپت‌نویسی/CI، به‌جای پرسیدن دستی، متغیر محیطی `BIMARZ_PROFILE_PASSWORD` را تنظیم کن.

### پلتفرم‌های پشتیبانی‌شده

| پلتفرم | وضعیت تشخیص خودکار | یادداشت |
|---|---|---|
| آرچ لینوکس (دسکتاپ) | ✅ | kill-switch سطح کرنل کامل در دسترس (با روت) |
| کالی NetHunter داخل Termux (proot/chroot) | ✅ | تشخیص از طریق نشانه‌های mount کرنل اندروید؛ kill-switch سطح کرنل بدون روت هاست ممکن نیست — به‌صورت خودکار به fallback نرم‌افزاری (قطع اتصال تمیز به‌جای قفل شبکه) سوییچ می‌کند |
| ترموکس ساده (بدون NetHunter) | ✅ | |
| WSL | ✅ | |
| سایر توزیع‌های لینوکس | عمومی | باید به‌عنوان `desktop_linux`/`other` شناسایی شود |

### مشارکت

Issue ها و Pull Request ها در ریپازیتوری GitHub پروژه پذیرفته می‌شوند. لطفاً
قبل از هر PR، `ruff check`/`ruff format`/`cargo clippy`/`cargo test`/`pytest` را
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
- A system-level kill-switch so no traffic leaks if the tunnel drops (with an honest software fallback in environments like Termux/proot that lack full kernel access)
- DNS leak protection by forcing DNS-over-HTTPS through the tunnel itself
- A single, coherent CLI with precise, understandable error messages

### Why this architecture?

| Layer | Language | Why |
|---|---|---|
| gRPC connection to xray-core, parallel health-checks, kill-switch, DNS guard | **Rust** | Performance and memory safety for hundreds of concurrent connections and precise network handling |
| CLI, profile management, subscription parsing, failover logic | **Python** | Development speed, readability, a pattern already proven in [open-downloader-cli](https://github.com/msoleimani62/open-downloader-cli) |

Full architectural reasoning, and real bugs found and fixed during development (including a critical routing bug and a critical kill-switch UID bug), are documented in `CHANGELOG.md`.

### Status & Roadmap

| Phase | Title | Status |
|---|---|---|
| 0 | gRPC proof-of-concept | ✅ Complete |
| 1 | Engine Adapter (real gRPC connection) | ✅ Complete — verified end-to-end against live xray-core |
| 2 | Profile & Subscription Manager | ✅ Complete — VLESS+Reality parsing, encrypted storage, `bimarz connect` |
| 3 | Health-check & automatic Failover | ✅ Complete — `bimarz healthcheck`, `bimarz connect --auto-failover` |
| 4 | Kill-switch & DNS leak guard | ✅ Complete — `bimarz killswitch`, `bimarz connect --killswitch` |
| 5 | CLI polish & packaging | ✅ Complete — layered doctor, release workflow, build script |
| 6 | Full test suite & CI | 🚧 Base CI ready (ruff+pytest+cargo), real xray-core integration test not yet added |
| 7 | Desktop GUI | ⏳ Not started |
| 8 | Android app | ⏳ Not started |

Every technical change is logged in [`CHANGELOG.md`](./CHANGELOG.md).

### Installation (from source — not yet published)

```bash
git clone https://github.com/msoleimani62/bimarz.git
cd bimarz
cat engine-core/proto/README.md
```

After reading the proto guide (the official xray-core proto files must be fetched separately):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
python3 -m venv .venv
source .venv/bin/activate
pip install maturin
maturin develop --release
bimarz doctor
```

### Usage

```bash
bimarz doctor                          # full check of environment, xray-core binary, profile status, kill-switch
bimarz doctor --xray-bin /path/xray    # explicit path to the xray-core binary
bimarz --debug doctor                  # show full technical traceback on failure

bimarz profile add "vless://..."       # add a profile from a VLESS+Reality+Vision share link
bimarz profile list                    # list saved profiles
bimarz profile remove <id>             # remove a profile by its id

bimarz healthcheck                     # check reachability/latency of all saved profiles in parallel

bimarz connect <id>                              # start xray-core and connect using a profile (Ctrl+C to disconnect)
bimarz connect <id> --auto-failover              # auto-switch to the best alternative on repeated failures
bimarz connect <id> --killswitch                 # prevent traffic leaks if the tunnel drops unexpectedly
bimarz connect <id> --auto-failover --killswitch # both together

bimarz killswitch enable --xray-uid $(id -u)     # manually activate the kill-switch (outside bimarz connect)
bimarz killswitch disable                        # deactivate it
bimarz killswitch status                         # show current status
```

Profiles are encrypted with a password (set the first time you save one). For scripting/CI, set the `BIMARZ_PROFILE_PASSWORD` environment variable instead of being prompted interactively.

### Supported platforms

| Platform | Auto-detection status | Notes |
|---|---|---|
| Arch Linux (desktop) | ✅ | Full kernel-level kill-switch available (with root) |
| Kali NetHunter inside Termux (proot/chroot) | ✅ | Detected via Android kernel mount signals; kernel-level kill-switch is not possible without host root — automatically falls back to the software path (clean disconnect instead of a network-wide lock) |
| Plain Termux (no NetHunter) | ✅ | |
| WSL | ✅ | |
| Other Linux distros | Generic | Should detect as `desktop_linux`/`other` |

### Contributing

Issues and Pull Requests are welcome on the project's GitHub repository.
Please run `ruff check`/`ruff format`/`cargo clippy`/`cargo test`/`pytest` clean
before opening a PR.

### License

MIT — see the `LICENSE` file.
