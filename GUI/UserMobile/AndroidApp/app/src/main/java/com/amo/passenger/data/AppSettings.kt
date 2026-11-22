package com.amo.passenger.data

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

internal enum class Language(val tag: String) {
    KOREAN("ko"),
    ENGLISH("en"),
    CHINESE("zh-Hans")
    ;

    companion object {
        fun from(locale: Locale): Language = when (locale.language) {
            "en" -> ENGLISH
            "zh" -> CHINESE
            else -> KOREAN
        }
    }
}

internal enum class ThemeMode {
    SYSTEM,
    LIGHT,
    DARK
}

/** Stores device-local language, theme, and tutorial preferences. */
internal class AppSettings(context: Context) {
    private val preferences = context.getSharedPreferences("amo_settings", Context.MODE_PRIVATE)
    private val systemLocale = context.resources.configuration.locales[0] ?: Locale.KOREAN

    var language: Language
        get() = Language.entries.firstOrNull { it.tag == preferences.getString("language", null) }
            ?: Language.from(systemLocale)
        set(value) = preferences.edit().putString("language", value.tag).apply()

    var theme: ThemeMode
        get() = ThemeMode.entries.firstOrNull { it.name == preferences.getString("theme", null) }
            ?: ThemeMode.SYSTEM
        set(value) = preferences.edit().putString("theme", value.name).apply()

    var tutorialEnabled: Boolean
        get() = preferences.getBoolean("tutorial_enabled", true)
        set(value) = preferences.edit().putBoolean("tutorial_enabled", value).apply()

    var tutorialSeen: Boolean
        get() = preferences.getBoolean("tutorial_seen", false)
        set(value) = preferences.edit().putBoolean("tutorial_seen", value).apply()

    fun localized(context: Context): Context {
        val configuration = Configuration(context.resources.configuration)
        val locale = Locale.forLanguageTag(language.tag)
        configuration.setLocale(locale)
        configuration.setLayoutDirection(locale)
        return context.createConfigurationContext(configuration)
    }

    fun isDark(configuration: Configuration): Boolean = when (theme) {
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
        ThemeMode.SYSTEM ->
            configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK ==
                Configuration.UI_MODE_NIGHT_YES
    }
}
