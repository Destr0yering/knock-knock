plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

val cognitoDomainUrl = providers.gradleProperty("cognitoDomainUrl").orElse("").get()
val cognitoClientId = providers.gradleProperty("cognitoClientId").orElse("").get()
val apiBaseUrl = providers.gradleProperty("apiBaseUrl")
    .orElse("https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/").get()
val firebaseConfig = file("google-services.json").takeIf { it.isFile }?.let {
    groovy.json.JsonSlurper().parse(it) as? Map<*, *>
}
val firebaseProjectInfo = firebaseConfig?.get("project_info") as? Map<*, *>
val firebaseClients = firebaseConfig?.get("client") as? List<*>
val firebaseClient = firebaseClients
    ?.mapNotNull { it as? Map<*, *> }
    ?.firstOrNull { client ->
        val clientInfo = client["client_info"] as? Map<*, *>
        val androidInfo = clientInfo?.get("android_client_info") as? Map<*, *>
        androidInfo?.get("package_name") == "com.knockknock.app"
    }
val firebaseClientInfo = firebaseClient?.get("client_info") as? Map<*, *>
val firebaseApiKeys = firebaseClient?.get("api_key") as? List<*>
val firebaseApiKeyEntry = firebaseApiKeys
    ?.mapNotNull { it as? Map<*, *> }
    ?.firstOrNull()
val firebaseProjectId = providers.gradleProperty("firebaseProjectId")
    .orElse(firebaseProjectInfo?.get("project_id") as? String ?: "").get()
val firebaseApplicationId = providers.gradleProperty("firebaseApplicationId")
    .orElse(firebaseClientInfo?.get("mobilesdk_app_id") as? String ?: "").get()
val firebaseApiKey = providers.gradleProperty("firebaseApiKey")
    .orElse(firebaseApiKeyEntry?.get("current_key") as? String ?: "").get()
val firebaseSenderId = providers.gradleProperty("firebaseSenderId")
    .orElse(firebaseProjectInfo?.get("project_number")?.toString() ?: "").get()
fun buildConfigString(value: String) = "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

android {
    namespace = "com.knockknock.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.knockknock.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        manifestPlaceholders["usesCleartextTraffic"] = "false"
        manifestPlaceholders["authRedirectScheme"] = "knockknock"
        buildConfigField("String", "COGNITO_DOMAIN_URL", "\"$cognitoDomainUrl\"")
        buildConfigField("String", "COGNITO_CLIENT_ID", "\"$cognitoClientId\"")
        buildConfigField("String", "API_BASE_URL", buildConfigString(apiBaseUrl))
        buildConfigField("String", "FIREBASE_PROJECT_ID", buildConfigString(firebaseProjectId))
        buildConfigField("String", "FIREBASE_APPLICATION_ID", buildConfigString(firebaseApplicationId))
        buildConfigField("String", "FIREBASE_API_KEY", buildConfigString(firebaseApiKey))
        buildConfigField("String", "FIREBASE_SENDER_ID", buildConfigString(firebaseSenderId))
    }

    buildTypes {
        debug {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
        }
        release {
            isMinifyEnabled = false
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
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging.resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
}

dependencies {
    implementation(project(":core:model"))
    implementation(project(":core:network"))
    implementation(project(":core:database"))
    implementation(project(":core:privacy"))
    implementation(project(":core:camera"))
    implementation(project(":core:vision"))
    implementation(project(":core:evidence"))
    implementation(project(":core:ui"))
    implementation(project(":feature:timeline"))
    implementation(project(":feature:review"))

    implementation(libs.androidx.core.ktx)
    implementation(libs.okhttp.core)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.fragment)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.work.runtime)
    implementation(platform(libs.androidx.compose.bom))
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.espresso)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
