import java.net.URI
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
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
            include("amo-logo-*.png", "amo-map-confirmed.png")
            into(outputDirectory)
        }
    }
}

val passengerAssets = tasks.register<PreparePassengerAssets>("preparePassengerAssets") {
    mapDirectory.set(rootProject.file("../../../maps"))
    outputDirectory.set(layout.buildDirectory.dir("generated/passenger-assets"))
}

/** Generates debug-only trust for the configured AMO HTTPS hostname. */
abstract class PreparePassengerNetwork : DefaultTask() {
    @get:Input
    abstract val apiHost: Property<String>

    @get:InputFile
    @get:Optional
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val caFile: RegularFileProperty

    @get:OutputDirectory
    abstract val outputDirectory: DirectoryProperty

    @TaskAction
    fun buildConfig() {
        val output = outputDirectory.get().asFile
        val raw = output.resolve("raw/amo_lan_ca.pem")
        val anchor = caFile.orNull?.asFile
        val lan = if (anchor == null) {
            raw.delete()
            ""
        } else {
            val certificates = anchor.inputStream().use {
                CertificateFactory.getInstance("X.509").generateCertificates(it)
            }
            require(
                certificates.isNotEmpty() && certificates.all {
                    it is X509Certificate && it.basicConstraints >= 0
                }
            ) { "amoLanCaFile must contain public CA certificates." }
            raw.parentFile.mkdirs()
            anchor.copyTo(raw, overwrite = true)
            """
            <domain-config cleartextTrafficPermitted="false">
                <domain includeSubdomains="false">${apiHost.get()}</domain>
                <trust-anchors><certificates src="@raw/amo_lan_ca" /></trust-anchors>
            </domain-config>
            """
        }
        val config = output.resolve("xml/amo_network.xml")
        config.parentFile.mkdirs()
        config.writeText(
            """
            <network-security-config>
                <base-config cleartextTrafficPermitted="false" />
                <domain-config cleartextTrafficPermitted="true">
                    <domain includeSubdomains="false">10.0.2.2</domain>
                    <domain includeSubdomains="false">127.0.0.1</domain>
                    <domain includeSubdomains="false">localhost</domain>
                </domain-config>
                $lan
            </network-security-config>
            """.trimIndent()
        )
    }
}

val privateCa = providers.gradleProperty("amoLanCaFile")
val usePrivateCa = privateCa.isPresent
require(
    !usePrivateCa ||
        (
            endpoint.scheme == "https" && endpoint.host !in setOf(
                "10.0.2.2",
                "127.0.0.1",
                "localhost"
            )
            )
) {
    "amoLanCaFile requires a non-loopback HTTPS AMO endpoint."
}
val passengerNetwork = tasks.register<PreparePassengerNetwork>("preparePassengerNetwork") {
    apiHost.set(endpoint.host)
    caFile.fileProvider(privateCa.map { file(it) })
    outputDirectory.set(layout.buildDirectory.dir("generated/passenger-network"))
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

androidComponents.onVariants(androidComponents.selector().withBuildType("debug")) { variant ->
    variant.sources.res?.addGeneratedSourceDirectory(
        passengerNetwork,
        PreparePassengerNetwork::outputDirectory
    )
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
