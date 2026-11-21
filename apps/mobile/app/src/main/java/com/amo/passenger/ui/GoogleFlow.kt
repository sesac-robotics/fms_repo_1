package com.amo.passenger.ui

import android.app.Activity
import androidx.credentials.exceptions.ClearCredentialException
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import com.amo.passenger.application.AmoViewModel
import com.amo.passenger.application.UiIssue
import com.amo.passenger.data.ApiFailure
import com.amo.passenger.data.ContractFailure
import com.amo.passenger.data.GoogleLogin
import java.io.IOException

/** Connects the Android account chooser to the passenger sign-in use case. */
internal class GoogleFlow(activity: Activity, private val model: AmoViewModel) {
    private val login = GoogleLogin(activity)

    suspend fun choose(onToken: (String) -> Unit) {
        try {
            val clientId = model.googleClientId()
            onToken(login.request(clientId))
        } catch (_: GetCredentialCancellationException) {
            return
        } catch (_: GetCredentialException) {
            model.report(UiIssue.GOOGLE_FAILED)
        } catch (_: ContractFailure) {
            model.report(UiIssue.GOOGLE_UNAVAILABLE)
        } catch (error: ApiFailure) {
            model.report(
                if (error.status in
                    disabledResponses
                ) {
                    UiIssue.GOOGLE_UNAVAILABLE
                } else {
                    UiIssue.SERVER
                }
            )
        } catch (_: IOException) {
            model.report(UiIssue.NETWORK)
        } catch (_: IllegalArgumentException) {
            model.report(UiIssue.GOOGLE_FAILED)
        }
    }

    suspend fun clear() {
        try {
            login.clear()
        } catch (_: ClearCredentialException) {
            // The app session is cleared independently of the provider state.
        }
    }

    private companion object {
        val disabledResponses = setOf(403, 404, 503)
    }
}
