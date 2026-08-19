// این فایل فقط پلاگین‌ها را برای زیرپروژه‌ها در دسترس می‌گذارد، خودش
// چیزی apply نمی‌کند (الگوی رسمی Android Gradle Plugin با version catalog).
// This file only makes plugins available to subprojects; it does not
// apply anything itself (the official AGP + version-catalog pattern).
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
}
