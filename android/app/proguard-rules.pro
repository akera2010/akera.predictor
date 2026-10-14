# ---- AKERATEN v.0.1 R8 rules ----
-keepattributes Signature, InnerClasses, EnclosingMethod, *Annotation*, Exceptions
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations, AnnotationDefault

# ---- App models & API (reflection by Retrofit / kotlinx.serialization) ----
-keep class com.akeraten.valuebetmonitor.data.model.** { *; }
-keep interface com.akeraten.valuebetmonitor.data.remote.ApiService { *; }

# ---- kotlinx.serialization ----
-dontnote kotlinx.serialization.**
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class com.akeraten.valuebetmonitor.**$$serializer { *; }
-keepclassmembers class com.akeraten.valuebetmonitor.** { *** Companion; }
-keepclasseswithmembers class com.akeraten.valuebetmonitor.** { kotlinx.serialization.KSerializer serializer(...); }

# ---- Retrofit ----
-keepclasseswithmembers interface * { @retrofit2.http.* <methods>; }
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation
-dontwarn retrofit2.**
-dontwarn javax.annotation.**
-dontwarn kotlin.Unit
-dontwarn retrofit2.KotlinExtensions
-dontwarn retrofit2.KotlinExtensions$*

# ---- OkHttp / Okio ----
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
-dontwarn org.codehaus.mojo.animal_sniffer.**
-dontwarn javax.annotation.**
-dontwarn org.jetbrains.annotations.**

# ---- DataStore (preferences) ----
-keepclassmembers class * extends androidx.datastore.preferences.protobuf.GeneratedMessageLite { <fields>; }
