# کلاس‌های تولیدشده‌ی uniffi با JNA به بازتاب (reflection) متکی‌اند؛
# R8/Proguard باید هم آن‌ها و هم JNA خودش را دست‌نخورده نگه دارد.
# uniffi's generated classes rely on JNA reflection; R8/Proguard must
# leave both them and JNA itself untouched.
-keep class ir.bimarz.app.uniffi.** { *; }
-keep class com.sun.jna.** { *; }
-dontwarn com.sun.jna.**
