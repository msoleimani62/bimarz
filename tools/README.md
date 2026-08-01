# bxt — BiMarz Test & AI-Context Exporter

[فارسی](#فارسی) | [English](#english)

---

## فارسی

### این ابزار چیست؟

`bxt` یک ابزار خط‌فرمان مستقل است (فقط کتابخانه‌ی استاندارد پایتون، بدون هیچ وابستگی بیرونی) که:

1. تست‌های راست (`cargo test`) و پایتون (`pytest`) پروژه‌ی BiMarz را پیدا و اجرا می‌کند.
2. اگر `pytest` در venv نصب نبود، خودش با `pip install pytest` نصبش می‌کند.
3. یک نمای درختی از کل پروژه می‌سازد (با نادیده‌گرفتن `target/`، `.venv/`، `__pycache__/`، `.git/` و مشابه).
4. محتوای فایل‌های اساسی پروژه (`.py .rs .toml .md .proto .cfg .ini .yaml .yml .sh .txt`) را جمع‌آوری می‌کند.
5. خطاهای شناخته‌شده‌ی محیطی (مثل نبود دسترسی root برای `nft` در تست‌های kill-switch) را خودکار تشخیص داده و در گزارش توضیح می‌دهد.
6. همه را در یک فایل مارک‌داون واحد می‌ریزد — مناسب برای دادن مستقیم به یک ایجنت هوش مصنوعی جهت فهم کامل پروژه.

### نصب

```bash
cp ~/bimarz/tools/bxt.py ~/.local/bin/bxt
chmod +x ~/.local/bin/bxt
which -a bxt
```

خروجی `which -a bxt` باید فقط یک مسیر نشان دهد. اگر بیشتر از یکی بود، نسخه‌های تکراری قدیمی را حذف کن تا از اجرای اشتباه جلوگیری شود.

### استفاده

اجرای ساده با پیش‌فرض‌ها (مسیر پروژه: `~/bimarz`، مسیر خروجی: `/sdcard/Download`، نام فایل: `bxt-report.md`):
```bash
bxt
```

با مسیر و نام دلخواه:
```bash
bxt --project ~/bimarz --output-name bimarz-ai-context.md
```

فقط ساخت گزارش بدون اجرای تست‌ها:
```bash
bxt --skip-tests
```

راهنمای کامل گزینه‌ها:
```bash
bxt --help
```

### ساختار گزارش خروجی

- `## Test results` — نتیجه‌ی هر suite تست (راست و پایتون)، با وضعیت PASS/FAIL
- `## Known issues` — فقط اگر الگوی خطای شناخته‌شده در خروجی تست‌ها پیدا شود
- `## Project tree` — نمای درختی کامل پروژه
- `## Essential files` — لیست و محتوای کامل فایل‌های اساسی (فایل‌های بزرگ‌تر از ۲۰۰ کیلوبایت رد می‌شوند و در گزارش اعلام می‌شود)

### نکته‌ی نگهداری

`bxt` هر بار گزارش را کاملاً از نو می‌سازد — یعنی هیچ ویرایش دستی روی فایل خروجی قبلی حفظ نمی‌شود. اگر نکته‌ای باید همیشه در گزارش باشد، آن را به‌عنوان یک الگوی جدید در `KNOWN_ISSUE_PATTERNS` داخل خود `bxt.py` اضافه کن، نه این‌که مستقیم روی فایل خروجی ویرایش بزنی.

---

## English

### What this is

`bxt` is a standalone command-line tool (Python standard library only, zero external dependencies) that:

1. Discovers and runs BiMarz's Rust (`cargo test`) and Python (`pytest`) test suites.
2. Auto-installs `pytest` into the venv if it's missing.
3. Builds a directory tree of the whole project (ignoring `target/`, `.venv/`, `__pycache__/`, `.git/`, and similar).
4. Collects the content of essential project files (`.py .rs .toml .md .proto .cfg .ini .yaml .yml .sh .txt`).
5. Auto-detects known environmental error patterns (e.g. missing root access for `nft` in kill-switch tests) and explains them in the report.
6. Bundles everything into a single markdown file — suitable for handing directly to an AI agent to fully understand the project.

### Install

```bash
cp ~/bimarz/tools/bxt.py ~/.local/bin/bxt
chmod +x ~/.local/bin/bxt
which -a bxt
```

`which -a bxt` should show exactly one path. If it shows more than one, remove the stale duplicates so the wrong version never runs.

### Usage

Run with defaults (project path: `~/bimarz`, output dir: `/sdcard/Download`, file name: `bxt-report.md`):
```bash
bxt
```

With a custom path and name:
```bash
bxt --project ~/bimarz --output-name bimarz-ai-context.md
```

Skip test execution and just export the report:
```bash
bxt --skip-tests
```

Full option reference:
```bash
bxt --help
```

### Report structure

- `## Test results` — outcome of every discovered suite (Rust and Python), PASS/FAIL status
- `## Known issues` — only present if a known error pattern is found in the test output
- `## Project tree` — full project directory tree
- `## Essential files` — the list and full content of essential files (files over 200 KB are skipped and noted in the report)

### Maintenance note

`bxt` rebuilds the report from scratch every run — any manual edit made to a previous output file is lost. If something should always appear in the report, add it as a new pattern in `KNOWN_ISSUE_PATTERNS` inside `bxt.py` itself, not by editing the output file directly.
