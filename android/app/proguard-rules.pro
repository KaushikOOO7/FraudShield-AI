# Retrofit keeps generic signatures and annotation metadata for service interfaces.
-keepattributes Signature,InnerClasses,EnclosingMethod,RuntimeVisibleAnnotations,AnnotationDefault
-keepclassmembers,allowoptimization class com.fraudshield.app.core.model.** {
    *** Companion;
}
-keepclasseswithmembers class * {
    kotlinx.serialization.KSerializer serializer(...);
}
