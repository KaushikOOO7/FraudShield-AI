package com.fraudshield.app.core.model

import java.security.MessageDigest

object SignalPolicy {
    private val keywords = listOf("otp", "kyc", "blocked", "lottery", "prize", "customs", "anydesk", "teamviewer",
        "urgent", "refund", "upi", "reward", "ओटीपी", "केवाईसी", "तुरंत", "रिफंड", "ಒಟಿಪಿ", "ಕೆವೈಸಿ", "ಮರುಪಾವತಿ")
    fun matches(text: String): Boolean = keywords.any { text.contains(it, ignoreCase = true) }
    fun allowed(preferences: ProtectionPreferences, permission: ProtectionPermission, granted: Boolean): Boolean =
        preferences.monitoring && preferences.monitoringConsent && preferences.cloudConsent && permission in preferences.enabled && granted
}

/** Monotonic times are supplied by the caller; bounded memory, no message storage. */
class SourceDebouncer(private val windowMillis: Long = 10 * 60 * 1000L) {
    private val sources = LinkedHashMap<String, Long>()
    @Synchronized fun accept(source: String, now: Long): Boolean {
        val key = MessageDigest.getInstance("SHA-256").digest(source.toByteArray()).joinToString("") { "%02x".format(it) }
        sources.entries.removeAll { now - it.value >= windowMillis }
        if (sources.containsKey(key)) return false
        if (sources.size >= 200) sources.remove(sources.keys.first())
        sources[key] = now
        return true
    }
}
