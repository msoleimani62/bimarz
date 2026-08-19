// این ریشه‌ی جدا برای پروژه‌ی اندروید است (کنار bimarz پایتون/Rust
// دسکتاپ در ریشه‌ی مخزن)، دقیقاً به همین دلیل که Android Studio باید
// این پوشه را جدا از پروژه‌ی اصلی باز کند.
//
// This is a separate Gradle root for the Android project (alongside the
// desktop Python/Rust bimarz project at the repo root) — Android Studio
// should open this "android/" folder specifically, not the repo root.

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "bimarz-android"
include(":app")
