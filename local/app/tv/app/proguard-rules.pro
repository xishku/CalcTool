# ========== 本应用 ==========
-keep class com.calctool.tv.** { *; }
-keep class com.calctool.tv.App
-keep class com.calctool.tv.models.** { *; }
-keep class com.calctool.tv.data.** { *; }
-keep class com.calctool.tv.parser.** { *; }
-keep class com.calctool.tv.ui.** { *; }

# ========== Kotlin ==========
-keep class kotlin.** { *; }
-keep class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions, EnclosingMethod
-keep class kotlin.Metadata { *; }

# ========== Leanback (TV) ==========
-keep class androidx.leanback.** { *; }
-dontwarn androidx.leanback.**
-keep class androidx.recyclerview.** { *; }
-dontwarn androidx.recyclerview.**

# ========== AppCompat / Fragment ==========
-keep class androidx.appcompat.** { *; }
-dontwarn androidx.appcompat.**
-keep class androidx.fragment.** { *; }
-dontwarn androidx.fragment.**

# ========== Lifecycle / ViewModel ==========
-keep class androidx.lifecycle.** { *; }
-dontwarn androidx.lifecycle.**

# ========== Compose ==========
-keep class androidx.compose.** { *; }
-dontwarn androidx.compose.**
-keep class androidx.tv.** { *; }
-dontwarn androidx.tv.**

# ========== Core KTX ==========
-keep class androidx.core.** { *; }
-dontwarn androidx.core.**

# ========== Activity ==========
-keep class androidx.activity.** { *; }
-dontwarn androidx.activity.**

# ========== OkHttp ==========
-keep class okhttp3.** { *; }
-dontwarn okhttp3.**
-keep class okio.** { *; }
-dontwarn okio.**

# ========== Jsoup ==========
-keep class org.jsoup.** { *; }
-dontwarn org.jsoup.**

# ========== Gson ==========
-keepattributes Signature
-keep class com.google.gson.** { *; }
-keep class com.google.gson.reflect.** { *; }

# ========== Media3 / ExoPlayer ==========
-keep class androidx.media3.** { *; }
-dontwarn androidx.media3.**

# ========== Coil ==========
-keep class coil.** { *; }
-dontwarn coil.**

# ========== DataStore ==========
-keep class androidx.datastore.** { *; }
-dontwarn androidx.datastore.**

# ========== 通用 ==========
-keepattributes SourceFile, LineNumberTable
-keep public class * extends android.app.Application
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Service
-keep public class * extends androidx.fragment.app.Fragment
-keep class android.support.v8.renderscript.** { *; }
