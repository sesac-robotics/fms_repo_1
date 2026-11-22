package com.amo.passenger.ui

import android.widget.LinearLayout
import android.widget.Switch
import com.amo.passenger.R
import com.amo.passenger.data.AppSettings
import com.amo.passenger.data.Language
import com.amo.passenger.data.ThemeMode

/** Displays and changes device-local preferences without a backend session. */
internal class SettingsPanel(private val widgets: AmoWidgets, private val settings: AppSettings) {
    fun build(
        languageChanged: (Language) -> Unit,
        themeChanged: (ThemeMode) -> Unit,
        replay: () -> Unit
    ): LinearLayout = with(widgets) {
        column().apply {
            add(text(string(R.string.settings), 28, bold = true))
            add(
                card().apply {
                    add(text(string(R.string.language), 17, bold = true))
                    add(
                        choice(
                            R.string.language,
                            Language.entries,
                            settings.language,
                            Language::label,
                            languageChanged
                        ),
                        8
                    )
                    add(text(string(R.string.theme), 17, bold = true), 18)
                    add(
                        choice(
                            R.string.theme,
                            ThemeMode.entries,
                            settings.theme,
                            ThemeMode::label,
                            themeChanged
                        ),
                        8
                    )
                },
                16
            )
            add(
                card().apply {
                    add(text(string(R.string.tutorial), 17, bold = true))
                    add(
                        Switch(context).apply {
                            text = string(R.string.tutorial_auto)
                            setTextColor(palette.ink)
                            minimumHeight = dp(48)
                            isChecked = settings.tutorialEnabled
                            setOnCheckedChangeListener { _, value ->
                                settings.tutorialEnabled =
                                    value
                            }
                        },
                        8
                    )
                    add(button(string(R.string.tutorial_replay), action = replay), 8)
                },
                12
            )
        }
    }

    private fun <T> choice(
        title: Int,
        values: List<T>,
        selected: T,
        label: (T) -> Int,
        apply: (T) -> Unit
    ) = with(widgets) {
        button(string(label(selected))) {
            dialog()
                .setTitle(title)
                .setSingleChoiceItems(
                    values.map { string(label(it)) }.toTypedArray(),
                    values.indexOf(selected)
                ) { dialog, index ->
                    dialog.dismiss()
                    apply(values[index])
                }
                .setNegativeButton(R.string.close, null)
                .show()
        }.apply { contentDescription = "${string(title)}. $text" }
    }
}
