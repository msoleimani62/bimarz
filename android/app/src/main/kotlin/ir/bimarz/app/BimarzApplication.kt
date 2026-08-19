package ir.bimarz.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class BimarzApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    // کانال نوتیفیکیشن باید قبل از شروع اولین foreground service ساخته
    // شده باشد؛ ساختنش اینجا (نه داخل خودِ سرویس) این را تضمین می‌کند.
    // The notification channel must exist before the first foreground
    // service starts; creating it here (not inside the service itself)
    // guarantees that.
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            VPN_NOTIFICATION_CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val VPN_NOTIFICATION_CHANNEL_ID = "bimarz_vpn_status"
    }
}
