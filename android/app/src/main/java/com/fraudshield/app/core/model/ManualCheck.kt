package com.fraudshield.app.core.model

import java.net.URI
import java.time.Instant
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Input classification only. Never computes a verdict or risk score. */
object ManualCheck {
    private val urlCandidate = Regex("(?i)(https?://\\S+|www\\.\\S+|(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,}(?:/\\S*)?)")
    fun request(input: String, caller: Boolean, locale: String): AnalyzeRequest {
        val text = input.trim()
        require(text.isNotEmpty() && text.length <= 4000) { "Enter up to 4,000 characters." }
        require(locale in setOf("en", "hi", "kn")) { "Choose a supported language." }
        val type: SignalType
        val payload = if (caller) {
            type = SignalType.CALL
            val phone = phone(text)
            buildJsonObject { put("phone", phone) }
        } else if (urlCandidate.matches(text)) {
            type = SignalType.URL
            val url = if (text.startsWith("http://", true) || text.startsWith("https://", true)) text else "https://$text"
            val uri = URI(url)
            require(uri.host != null && uri.userInfo == null && uri.scheme.lowercase() in setOf("http", "https")) { "Enter a valid public link without credentials." }
            buildJsonObject { put("url", url) }
        } else {
            type = SignalType.SMS
            buildJsonObject { put("text", redactOtp(text)) }
        }
        return AnalyzeRequest(type, payload, locale, Instant.now().toString())
    }

    fun phone(value: String): String {
        val cleaned = value.trim().replace(Regex("[ ()-]"), "")
        val number = if (cleaned.matches(Regex("[6-9][0-9]{9}"))) "+91$cleaned" else cleaned
        require(number.matches(Regex("\\+[1-9][0-9]{7,14}"))) { "Enter a valid number with country code, for example +91 followed by 10 digits." }
        return number
    }

    fun redactOtp(text: String): String = text.replace(
        Regex("(?i)(otp|one[- ]time password|ओटीपी|ಒಟಿಪಿ)\\s*(?:is|:|=|-)?\\s*([0-9]{4,8})\\b"),
        "$1 [redacted]",
    )
}
