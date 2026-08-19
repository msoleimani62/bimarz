package ir.bimarz.app.vpn

import android.app.Notification
import android.app.PendingIntent
import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.app.NotificationCompat
import ir.bimarz.app.BimarzApplication
import ir.bimarz.app.MainActivity
import ir.bimarz.app.R
import ir.bimarz.app.data.ProfileRepository
import ir.bimarz.app.data.ServerProfile
import ir.bimarz.app.uniffi.MobileEngineClient
import ir.bimarz.app.uniffi.VlessRealityProfile
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import java.io.File
import java.net.ServerSocket

/**
 * جریان کامل اتصال، دقیقاً هم‌راستا با همان چیزی که CLI دسکتاپ در
 * `bimarz connect` انجام می‌دهد، فقط با دو تفاوت اندروید-محور:
 * (۱) به‌جای خواندن مستقیم پکت از یک اینترفیس شبکه‌ی واقعی، از
 * VpnService.Builder یک TUN مجازی می‌سازیم و آن را با hev-socks5-tunnel
 * به SOCKS5 محلی xray وصل می‌کنیم؛ (۲) کنترل gRPC xray-core دیگر از
 * طریق pyo3 نیست، از طریق همان منطق Rust با بایندینگ uniffi
 * (mobile-core) است — نه بازنویسی، همان کد.
 *
 * ترتیب: ۱) پیدا کردن دو پورت آزاد محلی (socks, api)
 *         ۲) نوشتن کانفیگ xray روی دیسک (XrayConfigBuilder)
 *         ۳) اجرای فرآیند xray-core (XrayProcessManager)
 *         ۴) اتصال gRPC به api inbound و اضافه‌کردن outbound واقعی
 *            VLESS+Reality (mobile-core, همان ACTIVE_OUTBOUND_TAG)
 *         ۵) establish() کردن رابط TUN
 *         ۶) شروع hev-socks5-tunnel برای هدایت پکت‌های TUN به SOCKS5
 *         ۷) ارتقا به foreground service با نوتیفیکیشن دائمی
 *
 * The full connect flow, deliberately mirroring what desktop's
 * `bimarz connect` CLI does, with two Android-specific differences:
 * (1) instead of reading packets off a real network interface directly,
 * VpnService.Builder creates a virtual TUN and hev-socks5-tunnel bridges
 * it to xray's local SOCKS5; (2) xray-core's gRPC control is no longer
 * through pyo3, it's through the same Rust logic via uniffi bindings
 * (mobile-core) — not a rewrite, the same code.
 *
 * Order: 1) find two free local ports (socks, api)
 *        2) write the xray config to disk (XrayConfigBuilder)
 *        3) start the xray-core process (XrayProcessManager)
 *        4) gRPC-connect to the api inbound and add the real
 *           VLESS+Reality outbound (mobile-core, the same
 *           ACTIVE_OUTBOUND_TAG)
 *        5) establish() the TUN interface
 *        6) start hev-socks5-tunnel to forward TUN packets to SOCKS5
 *        7) promote to a foreground service with a persistent
 *           notification
 */
class BimarzVpnService : VpnService() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var profileRepository: ProfileRepository
    private val xrayProcessManager by lazy { XrayProcessManager(this) }
    private var tunInterface: ParcelFileDescriptor? = null
    private var engineClient: MobileEngineClient? = null
    private var tunnelThread: Thread? = null

    override fun onCreate() {
        super.onCreate()
        profileRepository = ProfileRepository(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_CONNECT -> {
                val profileId = intent.getStringExtra(EXTRA_PROFILE_ID)
                if (profileId != null) {
                    serviceScope.launch { connect(profileId) }
                }
            }
            ACTION_DISCONNECT -> serviceScope.launch { disconnect() }
        }
        return START_NOT_STICKY
    }

    override fun onRevoke() {
        // کاربر از تنظیمات سیستم مجوز VPN را لغو کرده — باید بلافاصله
        // تمیز جمع کنیم، نه منتظر یک اکشن DISCONNECT از UI بمانیم.
        // The user revoked VPN permission from system settings — must
        // clean up immediately, not wait for a DISCONNECT action from
        // the UI.
        serviceScope.launch { disconnect() }
        super.onRevoke()
    }

    override fun onDestroy() {
        serviceScope.launch { disconnect() }
        super.onDestroy()
    }

    private suspend fun connect(profileId: String) {
        VpnStateHolder.update(ConnectionState.Connecting)
        try {
            val profile = profileRepository.loadAll().firstOrNull { it.profileId == profileId }
                ?: throw IllegalStateException("Profile not found: $profileId")

            val socksPort = findFreePort()
            val apiPort = findFreePort()

            val configFile = File(filesDir, "xray-runtime-config.json")
            configFile.writeText(
                XrayConfigBuilder.build(XrayConfigBuilder.Ports(socksPort, apiPort)),
            )

            xrayProcessManager.start(configFile)

            val client = connectEngineWithRetry("http://127.0.0.1:$apiPort")
            client.addVlessRealityOutbound(profile.toUniffiProfile())
            engineClient = client

            tunInterface = establishTunInterface(profile)
            tunnelThread = startTunToSocksBridge(socksPort)

            startForeground(NOTIFICATION_ID, buildConnectedNotification())
            VpnStateHolder.update(ConnectionState.Connected(profile.profileId, profile.label))
        } catch (e: Exception) {
            Log.e(TAG, "connect() failed", e)
            VpnStateHolder.update(ConnectionState.Error(e.message ?: "Unknown error"))
            disconnect()
        }
    }

    private suspend fun disconnect() {
        VpnStateHolder.update(ConnectionState.Disconnecting)

        TunToSocksBridge.stop()
        tunnelThread?.interrupt()
        tunnelThread = null

        runCatching { tunInterface?.close() }
        tunInterface = null

        runCatching { engineClient?.removeOutbound(XrayConfigBuilder.ACTIVE_OUTBOUND_TAG) }
        engineClient = null

        xrayProcessManager.stop()

        stopForeground(STOP_FOREGROUND_REMOVE)
        VpnStateHolder.update(ConnectionState.Disconnected)
        stopSelf()
    }

    // xray-core بلافاصله بعد از start شدن، سرویس gRPC را در دسترس قرار
    // نمی‌دهد — یک تلاش-دوباره‌ی کوتاه و محدود لازم است، دقیقاً همان
    // مشکلی که در تست‌های healthcheck دسکتاپ هم دیده شده بود.
    // xray-core does not make the gRPC service available the instant it
    // starts — a short, bounded retry loop is needed, the exact same
    // issue seen in desktop's healthcheck tests.
    private suspend fun connectEngineWithRetry(endpoint: String): MobileEngineClient {
        val result = withTimeoutOrNull(ENGINE_CONNECT_TIMEOUT_MS) {
            var lastError: Exception? = null
            while (true) {
                try {
                    return@withTimeoutOrNull MobileEngineClient.connect(endpoint)
                } catch (e: Exception) {
                    lastError = e
                    delay(ENGINE_CONNECT_RETRY_DELAY_MS)
                }
            }
            @Suppress("UNREACHABLE_CODE")
            throw lastError ?: IllegalStateException("engine connect failed")
        }
        return result ?: throw IllegalStateException(
            "Timed out connecting to xray-core's gRPC API at $endpoint",
        )
    }

    private fun establishTunInterface(profile: ServerProfile): ParcelFileDescriptor {
        val builder = Builder()
            .setSession(getString(R.string.app_name))
            .addAddress(TUN_ADDRESS, TUN_PREFIX_LENGTH)
            .addRoute("0.0.0.0", 0)
            .addDnsServer(TUN_DNS_SERVER)
            .setMtu(TUN_MTU)
            .setBlocking(false)

        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        builder.setConfigureIntent(pendingIntent)

        return builder.establish()
            ?: throw IllegalStateException("VpnService.Builder.establish() returned null")
    }

    private fun startTunToSocksBridge(socksPort: Int): Thread {
        val tunFd = tunInterface?.fd
            ?: throw IllegalStateException("TUN interface is not established")
        val tun2socksConfig = File(filesDir, "tun2socks-runtime-config.json")
        tun2socksConfig.writeText(buildTun2SocksConfigJson(socksPort))

        val thread = Thread({
            TunToSocksBridge.start(tun2socksConfig.absolutePath, tunFd)
        }, "bimarz-tun2socks")
        thread.isDaemon = true
        thread.start()
        return thread
    }

    // ⚠️ ساختار واقعی این JSON باید طبق مستندات نسخه‌ای از
    // hev-socks5-tunnel که vendor می‌کنی تأیید شود؛ این نمونه بر اساس
    // فرمت رایج مستندشده‌ی بالادستی نوشته شده.
    // ⚠️ The real shape of this JSON must be confirmed against whatever
    // hev-socks5-tunnel version you vendor's own docs; this is written
    // per the commonly documented upstream format.
    private fun buildTun2SocksConfigJson(socksPort: Int): String = """
        {
          "tunnel": { "mtu": $TUN_MTU },
          "socks5": { "address": "127.0.0.1", "port": $socksPort, "udp": "udp" }
        }
    """.trimIndent()

    private fun findFreePort(): Int = ServerSocket(0).use { it.localPort }

    private fun buildConnectedNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, BimarzApplication.VPN_NOTIFICATION_CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_connected_title))
            .setContentText(getString(R.string.notification_connected_text))
            .setSmallIcon(android.R.drawable.ic_lock_lock)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun ServerProfile.toUniffiProfile(): VlessRealityProfile = VlessRealityProfile(
        tag = XrayConfigBuilder.ACTIVE_OUTBOUND_TAG,
        uuid = uuid,
        flow = flow,
        address = address,
        port = port.toUInt(),
        network = network,
        sni = sni,
        fingerprint = fingerprint,
        publicKeyB64 = publicKeyB64,
        shortIdHex = shortIdHex,
        spiderX = spiderX,
    )

    companion object {
        private const val TAG = "BimarzVpnService"
        private const val NOTIFICATION_ID = 1
        private const val TUN_ADDRESS = "10.10.10.1"
        private const val TUN_PREFIX_LENGTH = 32
        private const val TUN_DNS_SERVER = "1.1.1.1"
        private const val TUN_MTU = 1500
        private const val ENGINE_CONNECT_TIMEOUT_MS = 10_000L
        private const val ENGINE_CONNECT_RETRY_DELAY_MS = 200L

        const val ACTION_CONNECT = "ir.bimarz.app.action.CONNECT"
        const val ACTION_DISCONNECT = "ir.bimarz.app.action.DISCONNECT"
        const val EXTRA_PROFILE_ID = "ir.bimarz.app.extra.PROFILE_ID"
    }
}
