# Fetching the Official Xray-core Proto Files / واکشی فایل‌های proto رسمی Xray-core

فایل‌های `.proto` مستقیماً از مخزن رسمی `XTLS/xray-core` می‌آیند و در این
ریپازیتوری commit نمی‌شوند (چون باید همیشه با نسخه‌ی باینری xray-core که
واقعاً اجرا می‌کنی هماهنگ باشند). این کار را روی لپ‌تاپ Arch انجام بده، چون
به دسترسی شبکه نیاز دارد.

The `.proto` files come directly from the official `XTLS/xray-core`
repository and are intentionally **not** committed to this repo (they must
always match the exact xray-core binary version you run). Do this step on
the Arch laptop since it needs network access.

## Single source of truth / تنها مرجع معتبر نسخه

نسخه‌ی Xray فقط در یک جا پین می‌شود: `engine-core/xray-proto-pin.env`
(تگ + کامیت غیرقابل‌تغییر). اسکریپت واکشی، build.rs، گردش‌کارهای CI/release
و مستندات همه از همان فایل می‌خوانند. نسخه را هیچ‌جای دیگر hard-code نکن.

The Xray version is pinned in exactly one place:
`engine-core/xray-proto-pin.env` (tag + immutable commit). The fetch
script, `build.rs`, the CI/release workflows and the docs all read that
file. Never hard-code the version anywhere else.

## مراحل / Steps

```bash
# از ریشه‌ی ریپازیتوری — نسخه از xray-proto-pin.env خوانده می‌شود.
# From the repository root — the version is read from xray-proto-pin.env.
./scripts/fetch-protos.sh
```

The script:

- clones the pinned tag, then verifies the clone still points at the
  pinned immutable commit (a moved upstream tag fails loudly),
- verifies `app/` and `common/` exist and contain `.proto` files,
- wipes `proto/app` and `proto/common` before copying, so stale files
  from a previous fetch can never contaminate the build.

کلون تگ پین‌شده را می‌گیرد و بعد بررسی می‌کند کلون هنوز به همان کامیت
پین‌شده‌ی غیرقابل‌تغییر اشاره کند (جابه‌جاشدن تگ upstream با خطای واضح
متوقف می‌شود)، وجود `app/` و `common/` و فایل‌های `.proto` را بررسی
می‌کند، و قبل از کپی، مقصد را پاک می‌کند تا فایل‌های کهنه build را آلوده
نکنند.

کل درخت proto زیر `app/` و `common/` کپی می‌شود، نه فقط فایل‌های
`command.proto` — چون این فایل‌ها به فایل‌های دیگری (مثل
`app/proxyman/config.proto`) import می‌کنند و اگر آن وابستگی‌ها را کم
بگذاریم، prost-build مسیرهای `super::` را اشتباه محاسبه می‌کند (خطای
"too many leading super keywords").

We copy the ENTIRE proto tree under `app/` and `common/`, not just the
`command.proto` files — because those files import other files (e.g.
`app/proxyman/config.proto`), and leaving those dependencies out makes
prost-build miscalculate `super::` paths (the "too many leading super
keywords" error).

بعد از این مرحله، `cargo build` در `engine-core/` این فایل‌ها را به‌صورت
خودکار کامپایل می‌کند (طبق `build.rs`).

After this step, `cargo build` inside `engine-core/` will automatically
compile these files (per `build.rs`).

## Override for experiments / نادیده‌گرفتن پین برای آزمایش

```bash
XRAY_TAG="v25.3.6" ./scripts/fetch-protos.sh
```

این کار با یک هشدار پرصدا انجام می‌شود و کامیت غیرقابل‌تغییر در حالت
override بررسی نمی‌شود — فقط برای آزمایش، نه برای release.

This happens with a loud warning, and the immutable-commit check is
skipped in override mode — experiments only, never for a release.

## License / مجوز

Xray-core is licensed under the Mozilla Public License 2.0 (MPL-2.0);
see `LICENSE` in <https://github.com/XTLS/Xray-core>. The proto files are
fetched at build time and are **not** redistributed in this repository or
in the published wheels — only the generated Rust bindings are compiled
into the extension. Keep this attribution if you ever mirror or vendor
the proto tree.

Xray-core تحت مجوز Mozilla Public License 2.0 (MPL-2.0) منتشر می‌شود؛ به
`LICENSE` در <https://github.com/XTLS/Xray-core> مراجعه کن. فایل‌های proto
هنگام build واکشی می‌شوند و در این ریپازیتوری یا wheelهای منتشرشده
بازتوزیع **نمی‌شوند** — فقط bindingهای Rust تولیدشده داخل اکستنشن
کامپایل می‌شوند. اگر روزی درخت proto را mirror یا vendor کردی، این
اطلاعات attribution را نگه دار.

## نکته‌ی نگهداری نسخه / Version-tracking note

هر بار که نسخه‌ی باینری xray-core را آپدیت می‌کنی، تگ و کامیت جدید را در
`engine-core/xray-proto-pin.env` بنویس، `./scripts/fetch-protos.sh` را
اجرا کن و تغییر را در `CHANGELOG.md` ریشه‌ی پروژه ثبت کن.

Every time you upgrade the xray-core binary version, write the new tag
and commit into `engine-core/xray-proto-pin.env`, re-run
`./scripts/fetch-protos.sh`, and record the change in the project root
`CHANGELOG.md`.
