plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "ir.bimarz.app"
    // ۲۴ (اندروید ۷) چون VpnService.Builder.setMetered و برخی رفتارهای
    // مدرن‌تر VPN به همین حداقل نیاز دارند؛ پایین‌تر رفتن ارزش از دست‌
    // دادن این قابلیت‌ها را ندارد.
    // 24 (Android 7) because VpnService.Builder.setMetered and some newer
    // VPN behaviour needs this floor; going lower isn't worth losing them.
    compileSdk = 35

    defaultConfig {
        applicationId = "ir.bimarz.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    // scripts/build-android.sh دقیقاً همین چهار ABI را در
    // src/main/jniLibs/<abi>/ پر می‌کند (libmobile_core.so + باینری
    // xray بسته‌بندی‌شده + libhev-socks5-tunnel.so).
    // scripts/build-android.sh populates exactly these four ABIs under
    // src/main/jniLibs/<abi>/ (libmobile_core.so + the bundled xray
    // binary + libhev-socks5-tunnel.so).
    ndk {
        abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64", "x86")
    }

    packaging {
        // xray به‌صورت یک باینری اجرایی معمولی داخل jniLibs بسته‌بندی
        // می‌شود (همان ترفند رایج v2rayNG/NekoBox) تا سیستم PackageManager
        // به‌جای ما اجازه‌ی اجرا از دایرکتوری native-lib را بدهد؛ این
        // خط از فشرده‌سازی/حذف احتمالی آن توسط AGP جلوگیری می‌کند.
        // xray is bundled as a plain executable inside jniLibs (the same
        // trick v2rayNG/NekoBox use) so the PackageManager grants it
        // exec permission the way it does for native libraries; this
        // line stops AGP from compressing/stripping it away.
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)
    implementation(libs.androidx.security.crypto)
    implementation(libs.kotlinx.coroutines.android)
    debugImplementation(libs.androidx.compose.ui.tooling)

    // bindings تولیدشده توسط uniffi روی کاتلین متکی به JNA است تا
    // libmobile_core.so را در زمان اجرا لود کند.
    // uniffi's generated Kotlin bindings rely on JNA to load
    // libmobile_core.so at runtime.
    implementation("net.java.dev.jna:jna:5.14.0@aar")
}
