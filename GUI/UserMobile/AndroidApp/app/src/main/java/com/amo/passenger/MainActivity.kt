package com.amo.passenger

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.viewModels
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.amo.passenger.application.AmoUiState
import com.amo.passenger.application.AmoViewModel
import com.amo.passenger.application.Screen
import com.amo.passenger.data.AppSettings
import com.amo.passenger.ui.AccountPanel
import com.amo.passenger.ui.AmoPalette
import com.amo.passenger.ui.AmoShell
import com.amo.passenger.ui.AmoWidgets
import com.amo.passenger.ui.AuthForm
import com.amo.passenger.ui.GoogleFlow
import com.amo.passenger.ui.RidePanels
import com.amo.passenger.ui.SettingsPanel
import com.amo.passenger.ui.Tutorial
import kotlinx.coroutines.launch

/** Binds native Android controls to the application state and Android account chooser. */
class MainActivity : ComponentActivity() {
    private val model: AmoViewModel by viewModels()
    private lateinit var settings: AppSettings
    private lateinit var widgets: AmoWidgets
    private lateinit var shell: AmoShell
    private lateinit var tutorial: Tutorial
    private var currentScreen: Screen? = null
    private var previousScreen: Screen? = null
    private var form: AuthForm? = null
    private var googleBusy = false

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppSettings(newBase).localized(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = AppSettings(this)
        previousScreen = savedInstanceState?.getString("previous_screen")?.let(Screen::valueOf)
        widgets = AmoWidgets(this, AmoPalette.of(settings.isDark(resources.configuration)))
        tutorial = Tutorial(widgets, settings)
        shell = AmoShell(widgets, ::openSettings, ::closeSettings, model::navigate)
        showShell()
        configureBack()

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { model.state.collect(::render) }
                launch { model.followServerUpdates() }
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        previousScreen?.let { outState.putString("previous_screen", it.name) }
    }

    private fun showShell() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        shell.root.setBackgroundColor(widgets.palette.background)
        ViewCompat.setOnApplyWindowInsetsListener(shell.root) { view, insets ->
            val adjusted = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime()
            )
            view.setPadding(adjusted.left, adjusted.top, adjusted.right, adjusted.bottom)
            insets
        }
        setContentView(shell.root)
        WindowInsetsControllerCompat(window, shell.root).apply {
            isAppearanceLightStatusBars = !widgets.palette.dark
            isAppearanceLightNavigationBars = !widgets.palette.dark
        }
        ViewCompat.requestApplyInsets(shell.root)
    }

    private fun configureBack() {
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    when (model.state.value.screen) {
                        Screen.SETTINGS -> closeSettings()
                        Screen.REGISTER -> model.navigate(Screen.SIGN_IN)
                        Screen.HISTORY, Screen.PROFILE -> model.navigate(Screen.HOME)
                        else -> finish()
                    }
                }
            }
        )
    }

    private fun render(state: AmoUiState) {
        val screenChanged = currentScreen != state.screen
        currentScreen = state.screen
        shell.update(state)
        if (state.screen == Screen.SIGN_IN || state.screen == Screen.REGISTER) {
            showAuth(state, screenChanged)
            return
        }
        val screen = when (state.screen) {
            Screen.HOME -> RidePanels(widgets).home(
                state,
                settings.language.tag,
                model::chooseStop,
                model::requestRide,
                model::refreshTrips,
                model::prepareNewRide
            )
            Screen.HISTORY -> RidePanels(widgets).history(state, model::refreshTrips)
            Screen.PROFILE -> AccountPanel(widgets).profile(
                state,
                model::refreshProfile,
                { startGoogleFlow(model::linkGoogle) },
                ::signOut
            )
            Screen.SETTINGS -> SettingsPanel(widgets, settings).build(
                {
                    settings.language = it
                    recreate()
                },
                {
                    settings.theme = it
                    recreate()
                },
                tutorial::show
            )
            Screen.SIGN_IN, Screen.REGISTER -> error("Auth is rendered independently.")
        }
        shell.show(screen, screenChanged)
        if (state.screen == Screen.HOME && settings.tutorialEnabled && !settings.tutorialSeen &&
            !state.busy
        ) {
            tutorial.show()
        }
    }

    private fun showAuth(state: AmoUiState, screenChanged: Boolean) {
        val register = state.screen == Screen.REGISTER
        if (screenChanged || form == null) {
            form = AuthForm(
                widgets,
                register,
                model::signIn,
                model::register,
                { startGoogleFlow(model::signInGoogle) }
            ) { model.navigate(if (register) Screen.SIGN_IN else Screen.REGISTER) }
            shell.show(checkNotNull(form).view, true)
        }
        form?.update(state, googleBusy)
    }

    private fun openSettings() {
        previousScreen = model.state.value.screen
        model.navigate(Screen.SETTINGS)
    }

    private fun closeSettings() {
        val fallback = if (model.state.value.session == null) Screen.SIGN_IN else Screen.HOME
        model.navigate(previousScreen ?: fallback)
    }

    private fun startGoogleFlow(onToken: (String) -> Unit) {
        if (googleBusy) return
        googleBusy = true
        form?.update(model.state.value, true)
        lifecycleScope.launch {
            try {
                GoogleFlow(this@MainActivity, model).choose(onToken)
            } finally {
                googleBusy = false
                form?.update(model.state.value, false)
            }
        }
    }

    private fun signOut() {
        model.signOut()
        lifecycleScope.launch { GoogleFlow(this@MainActivity, model).clear() }
    }
}
