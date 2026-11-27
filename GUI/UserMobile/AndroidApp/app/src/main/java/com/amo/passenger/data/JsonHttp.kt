package com.amo.passenger.data

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
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

private const val MAX_RESPONSE_BYTES = 2_000_000

/** HTTP adapter scoped to the configured API origin. Each request has a five-second I/O timeout. */
internal class JsonHttp(base: String) {
    private val origin = URI(base)

    /**
     * Returns the UTF-8 JSON body, or an empty string for HTTP 204.
     * Throws [ApiFailure] on non-success status and [ContractFailure] above two million bytes.
     */
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
            val context = coroutineContext
            connection.inputStream.use { stream ->
                stream.readBoundedUtf8(MAX_RESPONSE_BYTES) { context.ensureActive() }
            }
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

/** Reads at most [limit] UTF-8 bytes from a borrowed stream, checking cancellation between reads. */
internal fun InputStream.readBoundedUtf8(limit: Int, checkActive: () -> Unit): String {
    require(limit > 0)
    val result = ByteArrayOutputStream()
    val chunk = ByteArray(8_192)
    while (true) {
        checkActive()
        val count = read(chunk, 0, minOf(chunk.size - 1, limit - result.size()) + 1)
        if (count < 0) return result.toString(Charsets.UTF_8.name())
        if (count > limit - result.size()) throw ContractFailure()
        result.write(chunk, 0, count)
    }
}
