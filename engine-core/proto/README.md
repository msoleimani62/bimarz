# Fetching the Official Xray-core Proto Files / واکشی فایل‌های proto رسمی Xray-core

فایل‌های `.proto` مستقیماً از مخزن رسمی `XTLS/xray-core` می‌آیند و در این
ریپازیتوری commit نمی‌شوند (چون باید همیشه با نسخه‌ی باینری xray-core که
واقعاً اجرا می‌کنی هماهنگ باشند). این کار را روی لپ‌تاپ Arch انجام بده، چون
به دسترسی شبکه نیاز دارد.

The `.proto` files come directly from the official `XTLS/xray-core`
repository and are intentionally **not** committed to this repo (they must
always match the exact xray-core binary version you run). Do this step on
the Arch laptop since it needs network access.

## مراحل / Steps

```bash
# نسخه‌ی xray-core که واقعاً اجرا می‌کنی را اینجا قفل کن (pin کن).
# Pin this to the exact xray-core version you actually run.
XRAY_TAG="v1.8.24"

git clone --depth 1 --branch "$XRAY_TAG" \
    https://github.com/XTLS/xray-core.git /tmp/xray-core-src

# کل درخت proto زیر app/ و common/ را کپی می‌کنیم، نه فقط فایل‌های
# command.proto — چون این فایل‌ها به فایل‌های دیگری (مثل app/proxyman/config.proto)
# import می‌کنند و اگر آن وابستگی‌ها را کم بگذاریم، prost-build مسیرهای
# super:: را اشتباه محاسبه می‌کند (خطای "too many leading super keywords").
#
# We copy the ENTIRE proto tree under app/ and common/, not just the
# command.proto files — because those files import other files (e.g.
# app/proxyman/config.proto), and leaving those dependencies out makes
# prost-build miscalculate super:: paths (the "too many leading super
# keywords" error).
mkdir -p proto
cp -r /tmp/xray-core-src/app proto/
cp -r /tmp/xray-core-src/common proto/

rm -rf /tmp/xray-core-src
```

بعد از این مرحله، `cargo build` در `engine-core/` این فایل‌ها را به‌صورت
خودکار کامپایل می‌کند (طبق `build.rs`).

After this step, `cargo build` inside `engine-core/` will automatically
compile these files (per `build.rs`).

## نکته‌ی نگهداری نسخه / Version-tracking note

هر بار که نسخه‌ی باینری xray-core را آپدیت می‌کنی، این مرحله را با
`XRAY_TAG` جدید تکرار کن و آن را در `CHANGELOG.md` ریشه‌ی پروژه ثبت کن.

Every time you upgrade the xray-core binary version, repeat this step with
the new `XRAY_TAG` and record it in the project root `CHANGELOG.md`.
