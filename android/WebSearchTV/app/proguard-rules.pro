# Add project specific ProGuard rules here.
# Keep Retrofit models
-keep class com.websearch.tv.api.** { *; }

# Keep Hilt generated classes
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
