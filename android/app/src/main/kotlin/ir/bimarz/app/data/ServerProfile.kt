package ir.bimarz.app.data

import java.util.UUID

/**
 * پروفایل یک سرور VLESS+Reality+Vision در سمت اندروید. عمداً مستقل از
 * مدل پروفایل پایتونِ دسکتاپ نگه داشته شده — پروفایل‌ها بین دستگاه‌ها
 * sync نمی‌شوند، هرکدام مستقل با چسباندن همان لینک vless:// اضافه
 * می‌شوند، پس نیازی به سازگاری باینری با فرمت ذخیره‌سازی دسکتاپ نیست.
 *
 * A VLESS+Reality+Vision server profile on the Android side. Deliberately
 * kept independent from the desktop Python profile model — profiles are
 * not synced between devices, each is added independently by pasting the
 * same vless:// link, so there is no need for binary compatibility with
 * desktop's storage format.
 */
data class ServerProfile(
    val profileId: String = UUID.randomUUID().toString(),
    val label: String,
    val tag: String,
    val uuid: String,
    val flow: String,
    val address: String,
    val port: Int,
    val network: String,
    val sni: String,
    val fingerprint: String,
    val publicKeyB64: String,
    val shortIdHex: String,
    val spiderX: String,
)
