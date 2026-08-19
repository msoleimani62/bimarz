# BiMarz Android — راهنمای راه‌اندازی / Setup Guide

<a name="fa"></a>
## فارسی

این پوشه یک پروژه‌ی Gradle **جدا** از پروژه‌ی پایتون/Rust دسکتاپ در ریشه‌ی
مخزن است. Android Studio باید مستقیماً همین پوشه‌ی `android/` را باز کند،
نه ریشه‌ی مخزن را.

### معماری خلاصه

- منطق واقعی (اتصال gRPC به xray-core، ساخت outbound از VLESS+Reality،
  health-check، کانفیگ DNS-guard) هیچ‌جا تکرار نشده — همان کد Rust
  تست‌شده‌ی `engine-core` است، فقط از طریق یک لایه‌ی نازک بایندینگ
  جدید (`mobile-core`, با uniffi-rs) به کاتلین صادر شده.
- xray-core خودش نمی‌تواند پکت خام یک رابط TUN را بخواند؛ فقط یک
  inbound SOCKS5/HTTP معمولی می‌فهمد. برای همین از **hev-socks5-tunnel**
  (همان ابزاری که NekoBox/sing-box-ui استفاده می‌کنند) به‌عنوان پل بین
  `VpnService` و SOCKS5 محلی xray استفاده شده.
- ذخیره‌سازی پروفایل با `EncryptedSharedPreferences` (کلید Keystore) است،
  نه PBKDF2+Fernet دسکتاپ — چون اندروید از قبل قفل‌صفحه + سخت‌افزار امن
  دارد و نیازی به رمز عبور جداگانه نیست.

### پیش‌نیازها

1. Android Studio (آخرین نسخه‌ی پایدار) + Android SDK
2. Android NDK (نصب از SDK Manager) و تنظیم متغیر محیطی:
   ```
   export ANDROID_NDK_HOME="$HOME/Android/Sdk/ndk/<نسخه>"
   ```
3. `cargo install cargo-ndk`
4. اهداف Rust برای هر چهار ABI:
   ```
   rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
   ```
5. باینری رسمی `xray` برای هر ABI (از انتشارهای رسمی XTLS/Xray-core) —
   هرکدام باید در `app/src/main/jniLibs/<abi>/libxray.so` قرار بگیرد
   (تغییر نام از `xray` به `libxray.so` عمدی است؛ همان ترفندی که
   PackageManager را وادار می‌کند مجوز اجرا بدهد).
6. یک build واقعی از **hev-socks5-tunnel** برای اندروید — سورس آن باید
   جداگانه واکشی/ساخته و `libhev-socks5-tunnel.so` در همان مسیر
   `jniLibs/<abi>/` قرار بگیرد. امضای JNI دقیق در
   `TunToSocksBridge.kt` باید در برابر همان نسخه‌ای که vendor می‌کنید
   تأیید شود.

### ساخت

```
cd android
../scripts/build-android.sh   # jniLibs/*.so + bindings کاتلین را می‌سازد
```

سپس در Android Studio پوشه‌ی `android/` را باز و Sync/Run کنید.

### وضعیت فعلی (صادقانه)

این اسکلت **کامپایل نشده و روی دستگاه واقعی تست نشده** — چون sandbox من
شبکه ندارد و Android SDK/NDK هم نصب نیست. طبق همان قانون همیشگی این
پروژه («هرگز ABI را حدس نزن»)، این کد با دقت روی سورس واقعی نوشته شده
ولی حتماً باید build شود و خطاهای واقعی برگردانده شوند تا اصلاح شوند —
دقیقاً همان چرخه‌ای که برای proto/gRPC هم جواب داد.

---

<a name="en"></a>
## English

This folder is a **separate** Gradle project from the desktop Python/Rust
project at the repo root. Android Studio should open this `android/`
folder directly, not the repo root.

### Architecture summary

- The real logic (gRPC connection to xray-core, building a VLESS+Reality
  outbound, health checks, DNS-guard config) is not duplicated anywhere —
  it's the exact same tested `engine-core` Rust code, exported to Kotlin
  through a thin new binding layer (`mobile-core`, via uniffi-rs).
- xray-core itself cannot read raw packets off a TUN interface; it only
  understands a plain SOCKS5/HTTP inbound. So **hev-socks5-tunnel** (the
  same tool NekoBox/sing-box-ui use) bridges `VpnService`'s TUN to xray's
  local SOCKS5.
- Profile storage uses `EncryptedSharedPreferences` (Keystore-backed key)
  instead of desktop's PBKDF2+Fernet — Android already has a lock screen
  and secure hardware, so no separate password is needed.

### Prerequisites

1. Android Studio (latest stable) + Android SDK
2. Android NDK (install via SDK Manager) and:
   ```
   export ANDROID_NDK_HOME="$HOME/Android/Sdk/ndk/<version>"
   ```
3. `cargo install cargo-ndk`
4. Rust targets for all four ABIs:
   ```
   rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
   ```
5. The official `xray` binary for each ABI (from XTLS/Xray-core official
   releases) — each must be placed at
   `app/src/main/jniLibs/<abi>/libxray.so` (the rename from `xray` to
   `libxray.so` is deliberate; it's the same trick that gets the
   PackageManager to grant exec permission).
6. A real Android build of **hev-socks5-tunnel** — its source must be
   fetched/built separately, with `libhev-socks5-tunnel.so` placed under
   the same `jniLibs/<abi>/` path. The exact JNI signature in
   `TunToSocksBridge.kt` must be confirmed against whichever version you
   vendor.

### Building

```
cd android
../scripts/build-android.sh   # builds jniLibs/*.so + Kotlin bindings
```

Then open the `android/` folder in Android Studio and Sync/Run.

### Current status (honestly)

This scaffold has **not been compiled or tested on a real device** —
my sandbox has no network and no Android SDK/NDK installed. Per this
project's standing rule ("never guess an ABI"), the code was written
carefully against the real source, but it genuinely needs to be built
and its real errors fed back for fixing — the same loop that worked for
the proto/gRPC work.
