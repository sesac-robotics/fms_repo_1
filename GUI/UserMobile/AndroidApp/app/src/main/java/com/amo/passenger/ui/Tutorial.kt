package com.amo.passenger.ui

import android.app.AlertDialog
import com.amo.passenger.R
import com.amo.passenger.data.AppSettings

/** Shows the first-use walkthrough and can replay it on request. */
internal class Tutorial(private val widgets: AmoWidgets, private val settings: AppSettings) {
    private val slides = listOf(
        R.string.tutorial_pickup_title to R.string.tutorial_pickup_body,
        R.string.tutorial_follow_title to R.string.tutorial_follow_body,
        R.string.tutorial_settings_title to R.string.tutorial_settings_body
    )
    private var dialog: AlertDialog? = null

    fun show() {
        if (dialog?.isShowing == true) return
        showSlide(0)
    }

    private fun showSlide(index: Int) {
        val (title, body) = slides[index]
        val finalSlide = index == slides.lastIndex
        val step = widgets.string(R.string.tutorial_step, index + 1, slides.size)
        dialog = widgets.dialog()
            .setTitle(title)
            .setMessage("$step\n\n${widgets.string(body)}")
            .setNegativeButton(R.string.skip) { _, _ -> finish() }
            .setPositiveButton(if (finalSlide) R.string.done else R.string.next) { _, _ ->
                if (finalSlide) finish() else showSlide(index + 1)
            }
            .setOnCancelListener { finish() }
            .show()
    }

    private fun finish() {
        settings.tutorialSeen = true
        dialog = null
    }
}
