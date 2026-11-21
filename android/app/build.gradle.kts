import java.net.URI
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.kapt")
    id("com.google.dagger.hilt.android")
}

val localConfig = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}
val configuredUrl = localConfig.getProperty("BACKEND_BASE_URL", "http://10.0.2.2:8000/")
require(configuredUrl.startsWith("https://") || configuredUrl.startsWith("http://")) {
    "BACKEND_BASE_URL must be an absolute HTTP(S) URL"
}
val baseUrl = configuredUrl.trimEnd('/') + "/"
val parsedBaseUrl = URI(baseUrl)
require(parsedBaseUrl.host != null && parsedBaseUrl.userInfo == null && parsedBaseUrl.query == null && parsedBaseUrl.fragment == null) {
    "BACKEND_BASE_URL must include a host and no credentials, query or fragment"
}
val urlLiteral = "\"" + baseUrl.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
val demoRequested = localConfig.getProperty("DEMO_MODE", "false").toBooleanStrictOrNull() ?: false
val backendReady = localConfig.containsKey("BACKEND_BASE_URL") &&
    localConfig.getProperty("BACKEND_CONTRACT_CONFIRMED", "false").toBooleanStrictOrNull() == true

android {
    namespace = "com.fraudshield.app"
    compileSdk = 34
    defaultConfig {
        applicationId = "in.fraudshield.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 2
        versionName = "0.2.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "BACKEND_BASE_URL", urlLiteral)
        buildConfigField("boolean", "DEMO_MODE", "false")
        buildConfigField("boolean", "BACKEND_READY", backendReady.toString())
        buildConfigField("boolean", "FEEDBACK_READY", localConfig.getProperty("FEEDBACK_CONTRACT_CONFIRMED", "false").toBooleanStrictOrNull()?.toString() ?: "false")
        buildConfigField("boolean", "EVIDENCE_READY", localConfig.getProperty("EVIDENCE_CONTRACT_CONFIRMED", "false").toBooleanStrictOrNull()?.toString() ?: "false")
        buildConfigField("boolean", "DELETION_READY", localConfig.getProperty("DELETION_CONTRACT_CONFIRMED", "false").toBooleanStrictOrNull()?.toString() ?: "false")
        buildConfigField("boolean", "REPORTS_IDEMPOTENT", localConfig.getProperty("REPORT_IDEMPOTENCY_CONFIRMED", "false").toBooleanStrictOrNull()?.toString() ?: "false")
        buildConfigField("boolean", "FAMILY_READY", localConfig.getProperty("FAMILY_ENROLLMENT_CONFIRMED", "false").toBooleanStrictOrNull()?.toString() ?: "false")
        vectorDrawables.useSupportLibrary = true
    }
    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            buildConfigField("boolean", "DEMO_MODE", demoRequested.toString())
            manifestPlaceholders["allowCleartext"] = "true"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            buildConfigField("boolean", "DEMO_MODE", "false")
            manifestPlaceholders["allowCleartext"] = "false"
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
    testOptions { unitTests.isReturnDefaultValues = true }
    sourceSets.getByName("main").assets.srcDir("src/main/assets")
    sourceSets.getByName("test").resources.srcDir("src/debug/assets")
}
kapt { correctErrorTypes = true }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.06.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.3")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("androidx.hilt:hilt-work:1.2.0")
    kapt("androidx.hilt:hilt-compiler:1.2.0")
    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-compiler:2.51.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")
    implementation("io.coil-kt:coil-compose:2.6.0")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")
    implementation("com.google.mlkit:barcode-scanning:17.2.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("app.cash.turbine:turbine:1.1.0")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
