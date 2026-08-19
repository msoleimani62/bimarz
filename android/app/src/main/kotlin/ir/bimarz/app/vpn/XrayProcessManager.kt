package ir.bimarz.app.vpn

import android.content.Context
import android.util.Log
import java.io.File

/**
 * باینری xray-core را (که در jniLibs/<abi>/libxray.so بسته‌بندی شده —
 * همان ترفند رایج v2rayNG/NekoBox که PackageManager را وادار می‌کند
 * مجوز اجرا به آن بدهد) به‌عنوان یک زیرفرآیند معمولی اجرا و مدیریت
 * می‌کند. هیچ پروتکل/رمزنگاری‌ای اینجا دوباره پیاده‌سازی نشده — دقیقاً
 * همان فلسفه‌ی «xray-core را دور نمی‌زنیم» که دسکتاپ هم رعایت می‌کند.
 *
 * Runs and manages the xray-core binary (bundled at
 * jniLibs/<abi>/libxray.so — the same trick v2rayNG/NekoBox use to make
 * PackageManager grant it exec permission) as a plain subprocess. No
 * protocol/crypto is reimplemented here — the exact same "never bypass
 * xray-core" philosophy desktop follows.
 */
class XrayProcessManager(private val context: Context) {

    private var process: Process? = null

    val isRunning: Boolean
        get() = process?.isAlive == true

    fun start(configFile: File): Process {
        check(!isRunning) { "xray is already running" }
        val binaryPath = File(context.applicationInfo.nativeLibraryDir, "libxray.so").absolutePath
        val builder = ProcessBuilder(binaryPath, "run", "-config", configFile.absolutePath)
            .redirectErrorStream(true)
            .directory(context.filesDir)
        val started = builder.start()
        process = started
        Log.i(TAG, "xray-core started (pid=${started.pid()})")
        return started
    }

    fun stop() {
        val current = process ?: return
        if (current.isAlive) {
            current.destroy()
            if (!current.waitFor(3, java.util.concurrent.TimeUnit.SECONDS)) {
                current.destroyForcibly()
            }
        }
        process = null
        Log.i(TAG, "xray-core stopped")
    }

    companion object {
        private const val TAG = "XrayProcessManager"
    }
}
