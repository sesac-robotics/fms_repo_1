package com.amo.passenger.ui

import android.graphics.Color

internal data class AmoPalette(
    val background: Int,
    val card: Int,
    val header: Int,
    val ink: Int,
    val muted: Int,
    val outline: Int,
    val accent: Int,
    val action: Int,
    val actionText: Int,
    val badge: Int,
    val error: Int,
    val dark: Boolean
) {
    companion object {
        fun of(dark: Boolean): AmoPalette = if (dark) {
            AmoPalette(
                color("#1A1321"), color("#2C2234"), color("#33243D"), color("#F0E3F2"),
                color("#C5B3CB"), color("#AB94B4"), color("#BBAAFF"), color("#FFABD0"),
                color("#2B1627"), color("#302038"), color("#FFC0D2"), true
            )
        } else {
            AmoPalette(
                color("#F5EFF6"), color("#FCF9FC"), color("#EFE5F1"), color("#35273D"),
                color("#63536A"), color("#8A718E"), color("#5444B8"), color("#432C4D"),
                color("#FCF9FC"), color("#F3E8F5"), color("#92244A"), false
            )
        }

        private fun color(value: String): Int = Color.parseColor(value)
    }
}
