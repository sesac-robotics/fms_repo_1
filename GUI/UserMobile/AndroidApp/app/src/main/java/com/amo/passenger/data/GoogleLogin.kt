package com.amo.passenger.data

import android.app.Activity
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

/** Obtains and returns the Google ID token for the backend's trusted audience. */
internal class GoogleLogin(private val activity: Activity) {
    private val manager = CredentialManager.create(activity)

    suspend fun request(clientId: String): String {
        val option = GetSignInWithGoogleOption.Builder(clientId).build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        val credential = manager.getCredential(activity, request).credential
        if (
            credential !is CustomCredential ||
            credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            throw ContractFailure()
        }
        return GoogleIdTokenCredential.createFrom(credential.data).idToken
    }

    suspend fun clear() {
        manager.clearCredentialState(ClearCredentialStateRequest())
    }
}
