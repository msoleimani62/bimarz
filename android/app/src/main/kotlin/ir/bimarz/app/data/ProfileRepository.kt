package ir.bimarz.app.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * ذخیره‌سازی پروفایل‌ها روی اندروید عمداً متفاوت از دسکتاپ است: دسکتاپ
 * از PBKDF2+Fernet با رمز عبوری که کاربر تایپ می‌کند استفاده می‌کند
 * (چون یک محیط چندکاربره‌ی بدون قفل‌صفحه‌ی سیستم‌عاملی است)، ولی اندروید
 * از قبل یک قفل‌صفحه + Keystore پشتیبان سخت‌افزاری دارد؛ به همین دلیل
 * اینجا از EncryptedSharedPreferences با کلید Keystore استفاده شده —
 * بدون نیاز به این‌که کاربر رمز عبور جداگانه‌ای تایپ کند. این یک تصمیم
 * معماری عمدی است، نه یک نقص نسبت به دسکتاپ.
 *
 * Storage on Android is deliberately different from desktop: desktop
 * uses PBKDF2+Fernet with a password the user types (since it's a
 * multi-user environment with no OS-level lock screen guarantee), but
 * Android already has a lock screen + hardware-backed Keystore; so this
 * uses EncryptedSharedPreferences with a Keystore-derived key instead —
 * no separate password required from the user. This is a deliberate
 * architecture decision, not a gap relative to desktop.
 */
class ProfileRepository(context: Context) {

    private val prefs = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            PREFS_FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    suspend fun loadAll(): List<ServerProfile> = withContext(Dispatchers.IO) {
        val raw = prefs.getString(PROFILES_KEY, null) ?: return@withContext emptyList()
        val array = JSONArray(raw)
        (0 until array.length()).map { i -> array.getJSONObject(i).toServerProfile() }
    }

    suspend fun save(profiles: List<ServerProfile>) = withContext(Dispatchers.IO) {
        val array = JSONArray()
        profiles.forEach { array.put(it.toJson()) }
        prefs.edit().putString(PROFILES_KEY, array.toString()).apply()
    }

    suspend fun add(profile: ServerProfile) {
        save(loadAll() + profile)
    }

    suspend fun remove(profileId: String) {
        save(loadAll().filterNot { it.profileId == profileId })
    }

    private fun ServerProfile.toJson(): JSONObject = JSONObject().apply {
        put("profileId", profileId)
        put("label", label)
        put("tag", tag)
        put("uuid", uuid)
        put("flow", flow)
        put("address", address)
        put("port", port)
        put("network", network)
        put("sni", sni)
        put("fingerprint", fingerprint)
        put("publicKeyB64", publicKeyB64)
        put("shortIdHex", shortIdHex)
        put("spiderX", spiderX)
    }

    private fun JSONObject.toServerProfile(): ServerProfile = ServerProfile(
        profileId = getString("profileId"),
        label = getString("label"),
        tag = getString("tag"),
        uuid = getString("uuid"),
        flow = getString("flow"),
        address = getString("address"),
        port = getInt("port"),
        network = getString("network"),
        sni = getString("sni"),
        fingerprint = getString("fingerprint"),
        publicKeyB64 = getString("publicKeyB64"),
        shortIdHex = getString("shortIdHex"),
        spiderX = getString("spiderX"),
    )

    companion object {
        private const val PREFS_FILE_NAME = "bimarz_profiles"
        private const val PROFILES_KEY = "profiles_json"
    }
}
