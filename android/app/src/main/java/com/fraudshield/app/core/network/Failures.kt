package com.fraudshield.app.core.network

import android.util.Log
import com.fraudshield.app.core.model.ApiErrorEnvelope
import com.fraudshield.app.core.model.UiState
import java.io.IOException
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import retrofit2.HttpException

class BackendFailure(val code: String, override val message: String, val retryable: Boolean) : IOException(message)

internal fun Throwable.toUiError(): UiState.Error {
    if (this is CancellationException) throw this
    if (this is Error) throw this
    // Log only the exception type: request bodies, tokens and evidence stay out of logs.
    Log.w("FraudShield", "Operation failed: ${javaClass.simpleName}")
    return when (this) {
        is BackendFailure -> UiState.Error(userMessage(code), retryable, code)
        is HttpException -> UiState.Error("The service could not complete this check. Try again shortly.", code() >= 500 || code() == 429, "SERVICE_UNAVAILABLE")
        is SerializationException -> UiState.Error("The service returned an unsupported response. Please try again later.", false, "INVALID_RESPONSE")
        is IOException -> UiState.Error("Cannot reach the service. Check your connection and try again.", code = "OFFLINE")
        else -> UiState.Error("This check could not finish. Please try again.", code = "UNKNOWN")
    }
}

internal fun userMessage(code: String): String = when (code) {
    "RATE_LIMITED" -> "Too many checks right now. Wait a moment, then try again."
    "UNAUTHORIZED", "TOKEN_EXPIRED" -> "Your device session needs to be renewed. Please retry."
    "INVALID_PAYLOAD", "VALIDATION_ERROR" -> "Check the information you entered and try again."
    "NOT_FOUND", "CASE_NOT_FOUND" -> "This case is no longer available."
    "SERVICE_UNAVAILABLE", "MODEL_UNAVAILABLE" -> "The investigation service is temporarily unavailable."
    "CONSENT_REQUIRED" -> "Review your consent settings before sending information."
    "BACKEND_NOT_CONFIGURED" -> "Cloud checks are not configured yet. Saved checks and emergency help are available."
    "FEATURE_UNAVAILABLE" -> "This service operation is awaiting the backend contract."
    else -> "The service could not complete this request. Try again shortly."
}

internal fun HttpException.backendFailure(json: Json): BackendFailure {
    val body = response()?.errorBody()?.string()
    val envelope = try {
        body?.let { json.decodeFromString<ApiErrorEnvelope>(it) }
    } catch (error: SerializationException) {
        Log.w("FraudShield", "Unrecognized error schema: ${error.javaClass.simpleName}")
        null
    } catch (error: IllegalArgumentException) {
        Log.w("FraudShield", "Invalid error schema: ${error.javaClass.simpleName}")
        null
    }
    return envelope?.error?.let { BackendFailure(it.code, it.message, it.retryable) }
        ?: BackendFailure("HTTP_${code()}", "HTTP ${code()}", code() >= 500 || code() == 429)
}
