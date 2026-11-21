package com.amo.passenger.data

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import org.json.JSONException
import org.json.JSONObject

internal class ApiFailure(val status: Int, val code: String? = null) :
    IOException("AMO API returned HTTP $status")
internal class ContractFailure : IOException("The AMO API response does not match its contract.")
internal class RoleFailure : IOException("The session is not a passenger session.")

/** HTTP adapter scoped to the configured API origin. Each request has a five-second I/O timeout. */
internal class JsonHttp(base: String) {
    private val origin = URI(base)

    suspend fun send(
        path: String,
        token: String? = null,
        body: JSONObject? = null,
        post: Boolean = body != null
    ): String = withContext(Dispatchers.IO) {
        require(path.startsWith("/api/") && !path.startsWith("//"))
        val connection = origin.resolve(path).toURL().openConnection() as HttpURLConnection
        try {
            connection.requestMethod = if (post) "POST" else "GET"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 5_000
            connection.readTimeout = 5_000
            connection.setRequestProperty("Accept", "application/json")
            if (token != null) connection.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.bufferedWriter(Charsets.UTF_8).use {
                    it.write(body.toString())
                }
            }
            val status = connection.responseCode
            coroutineContext.ensureActive()
            if (status !in 200..299) throw ApiFailure(status, failureCode(connection))
            if (status == 204) return@withContext ""
            connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }
    private fun failureCode(connection: HttpURLConnection): String? = try {
        connection.errorStream?.bufferedReader(Charsets.UTF_8)?.use { reader ->
            val sample = CharArray(1024)
            val count = reader.read(sample)
            if (count < 1) null else JSONObject(String(sample, 0, count)).optString("code")
        }
    } catch (_: JSONException) {
        null
    } catch (_: IOException) {
        null
    }
}
