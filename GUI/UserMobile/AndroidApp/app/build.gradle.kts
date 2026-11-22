import java.net.URI
import javax.inject.Inject

plugins {
    id("com.android.application") version "9.3.1"
}

val apiBase = providers.gradleProperty("amoApiUrl")
    .orElse(providers.environmentVariable("AMO_API_URL"))
    .orElse("http://10.0.2.2:18085")
    .get()
    .trim()
    .trimEnd('/')
val endpoint = URI(apiBase)
require(
    endpoint.scheme in setOf("http", "https") && endpoint.host != null &&
        endpoint.userInfo == null && endpoint.query == null && endpoint.fragment == null &&
        endpoint.path.isNullOrEmpty()
) { "AMO_API_URL must contain the HTTP(S) scheme, host, and optional port only." }

abstract class PreparePassengerAssets : DefaultTask() {
    @get:InputDirectory
    abstract val mapDirectory: DirectoryProperty

    @get:OutputDirectory
    abstract val outputDirectory: DirectoryProperty

    @get:Inject
    abstract val fileOperations: FileSystemOperations

    @TaskAction
    fun stage() {
        fileOperations.sync {
            from(mapDirectory)
            include("amo-logo-*.png", "amode-map-v02-passenger-*.png")
            into(outputDirectory)
        }
    }
}

val passengerAssets = tasks.register<PreparePassengerAssets>("preparePassengerAssets") {
    mapDirectory.set(rootProject.file("../../../maps"))
    outputDirectory.set(layout.buildDirectory.dir("generated/passenger-assets"))
}

android {
    namespace = "com.amo.passenger"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.amo.passenger"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        buildConfigField("String", "API_BASE_URL", "\"$apiBase\"")
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

androidComponents.onVariants { variant ->
    variant.sources.assets?.addGeneratedSourceDirectory(
        passengerAssets,
        PreparePassengerAssets::outputDirectory
    )
}

dependencies {
    implementation("androidx.activity:activity-ktx:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.10.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.credentials:credentials:1.5.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.5.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    testImplementation("junit:junit:4.13.2")
}

val ktlint by configurations.creating

dependencies {
    ktlint("com.pinterest.ktlint:ktlint-cli:1.7.1")
}

listOf("ktlintCheck", "ktlintFormat").forEach { taskName ->
    tasks.register<JavaExec>(taskName) {
        group = "verification"
        classpath = ktlint
        mainClass.set("com.pinterest.ktlint.Main")
        workingDir = rootProject.projectDir
        if (taskName == "ktlintFormat") args("--format")
        args("**/*.kt", "**/*.kts", "!**/build/**")
    }
}
