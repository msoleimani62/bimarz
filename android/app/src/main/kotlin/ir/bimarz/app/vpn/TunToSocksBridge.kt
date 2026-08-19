package ir.bimarz.app.vpn

/**
 * xray-core خودش پکت IP از یک رابط TUN نمی‌خواند — فقط یک inbound
 * SOCKS5/HTTP معمولی می‌فهمد. برای همین، مثل v2rayNG/NekoBox، پکت‌های
 * خام رابط TUN باید توسط یک ابزار جدا («tun2socks») به یک اتصال SOCKS5
 * محلی تبدیل شوند. اینجا از hev-socks5-tunnel استفاده شده (کوچک، فعال،
 * نوشته‌شده به C، دقیقاً همان ابزاری که NekoBox/sing-box-ui هم استفاده
 * می‌کنند) — نه یک پیاده‌سازی جدید.
 *
 * ⚠️ این کلاس فقط یک قرارداد JNI را تعریف می‌کند؛ نام دقیق تابع/امضا
 * باید در برابر همان نسخه‌ی واقعی hev-socks5-tunnel-android که vendor
 * می‌کنی تأیید شود (فورک‌های مختلف امضای کمی متفاوت دارند) — دقیقاً طبق
 * قانون همیشگی این پروژه: هرگز ABI را حدس نزن، همیشه خروجی واقعی را
 * چک کن. libhev-socks5-tunnel.so باید در jniLibs/<abi>/ کنار سایر .so
 * ها قرار بگیرد.
 *
 * xray-core itself does not read IP packets off a TUN interface — it
 * only understands a plain SOCKS5/HTTP inbound. So, like v2rayNG/NekoBox,
 * the TUN interface's raw packets need a separate tool ("tun2socks") to
 * turn them into a local SOCKS5 connection. This uses hev-socks5-tunnel
 * (small, actively maintained, written in C, the exact tool
 * NekoBox/sing-box-ui also use) — not a new implementation.
 *
 * ⚠️ This class only defines a JNI contract; the exact function name and
 * signature must be verified against whichever real
 * hev-socks5-tunnel-android build you vendor (forks differ slightly) —
 * per this project's standing rule: never guess an ABI, always check the
 * real output. libhev-socks5-tunnel.so must sit in jniLibs/<abi>/
 * alongside the other .so files.
 */
object TunToSocksBridge {

    init {
        System.loadLibrary("hev-socks5-tunnel")
    }

    /**
     * تونل را در یک نخ بلاک‌کننده‌ی جدا شروع می‌کند: پکت‌های رابط TUN
     * (با فایل‌دیسکریپتور `tunFd`، از VpnService.Builder().establish()
     * گرفته شده) را می‌خواند و به آدرس SOCKS5 مشخص‌شده در فایل کانفیگ
     * هدایت می‌کند. تا زمان توقف، برنمی‌گردد؛ باید از یک coroutine/نخ
     * پس‌زمینه صدا زده شود، نه از رشته‌ی UI.
     *
     * Starts the tunnel on a separate blocking thread: reads packets off
     * the TUN interface (via file descriptor `tunFd`, obtained from
     * VpnService.Builder().establish()) and forwards them to the SOCKS5
     * address given in the config file. Does not return until stopped;
     * must be invoked from a background coroutine/thread, never the UI
     * thread.
     */
    external fun start(configPath: String, tunFd: Int): Int

    external fun stop()
}
