package com.amo.passenger.ui

import android.app.AlertDialog
import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.view.ContextThemeWrapper
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.annotation.StringRes
import java.io.IOException
import kotlin.math.roundToInt

/** Shared visual boundaries for the native Android screens. Dimensions are in dp. */
internal class AmoWidgets(val context: Context, val palette: AmoPalette) {
    fun dp(value: Int): Int = (value * context.resources.displayMetrics.density).roundToInt()

    fun string(@StringRes id: Int, vararg args: Any): String = context.getString(id, *args)

    fun column(): LinearLayout = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
    }

    fun row(): LinearLayout = LinearLayout(context).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
    }

    fun rounded(color: Int, corner: Int, stroke: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(corner).toFloat()
            if (stroke != null) setStroke(dp(1), stroke)
        }

    fun card(): LinearLayout = column().apply {
        background = rounded(palette.card, 20, palette.outline)
        setPadding(dp(18), dp(16), dp(18), dp(16))
    }

    fun text(value: String, size: Int = 16, color: Int = palette.ink, bold: Boolean = false) =
        TextView(context).apply {
            text = value
            textSize = size.toFloat()
            setTextColor(color)
            if (bold) setTypeface(typeface, Typeface.BOLD)
        }

    fun button(value: String, primary: Boolean = false, action: () -> Unit): Button =
        Button(context).apply {
            text = value
            isAllCaps = false
            textSize = 15f
            minHeight = dp(48)
            minimumHeight = dp(48)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setTextColor(if (primary) palette.actionText else palette.ink)
            background = if (primary) {
                rounded(palette.action, 14)
            } else {
                rounded(palette.header, 14, palette.outline)
            }
            setOnClickListener { action() }
        }

    fun LinearLayout.add(item: View, top: Int = 0) {
        addView(
            item,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dp(top)
            }
        )
    }

    fun scroll(content: LinearLayout): ScrollView = ScrollView(context).apply {
        isFillViewport = true
        addView(content)
    }

    fun image(asset: String, description: String, height: Int, width: Int? = null): ImageView? {
        val image = try {
            context.assets.open(asset).use { Drawable.createFromStream(it, asset) }
        } catch (_: IOException) {
            null
        } ?: return null
        return ImageView(context).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            setImageDrawable(image)
            contentDescription = description
            layoutParams = LinearLayout.LayoutParams(
                width?.let(::dp) ?: ViewGroup.LayoutParams.MATCH_PARENT,
                dp(height)
            )
        }
    }

    fun dialog(): AlertDialog.Builder {
        val style = if (palette.dark) {
            android.R.style.Theme_Material_Dialog_Alert
        } else {
            android.R.style.Theme_Material_Light_Dialog_Alert
        }
        return AlertDialog.Builder(ContextThemeWrapper(context, style))
    }
}
