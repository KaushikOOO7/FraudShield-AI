package com.fraudshield.app.core.model

import kotlinx.serialization.Serializable

@Serializable
enum class ProtectionPermission { NOTIFICATIONS, CALLS, SMS, WARNINGS, CAMERA, CONTACTS }
enum class ProtectionStatus { PROTECTED, ATTENTION, PAUSED }
enum class CaseSource { SERVICE, SAVED, DEMO }
data class LocalCaseMetadata(val source: CaseSource, val savedAt: Long)

data class ProtectionPreferences(
    val onboardingComplete: Boolean = false,
    val monitoring: Boolean = false,
    val monitoringConsent: Boolean = false,
    val cloudConsent: Boolean = false,
    val enabled: Set<ProtectionPermission> = emptySet(),
    val allowedPackages: Set<String> = emptySet(),
    val previouslyGranted: Set<ProtectionPermission> = emptySet(),
    val revoked: Set<ProtectionPermission> = emptySet(),
    val lastCheckFailed: Boolean = false,
)

data class NotificationApp(val packageName: String, val label: String)
data class PermissionHealth(
    val granted: Set<ProtectionPermission> = emptySet(),
    val supported: Set<ProtectionPermission> = ProtectionPermission.entries.toSet(),
    val online: Boolean = false,
    val preferences: ProtectionPreferences = ProtectionPreferences(),
    val availableApps: List<NotificationApp> = emptyList(),
    val demo: Boolean = false,
    val backendReady: Boolean = false,
    val backendAvailable: Boolean = false,
) {
    val revoked: Set<ProtectionPermission> get() = preferences.revoked.intersect(preferences.enabled)
    val activeSources: Int get() = preferences.enabled.intersect(granted).count {
        it == ProtectionPermission.SMS || it == ProtectionPermission.CALLS ||
            (it == ProtectionPermission.NOTIFICATIONS && preferences.allowedPackages.isNotEmpty())
    }
    val status: ProtectionStatus get() = when {
        !preferences.monitoring || !preferences.monitoringConsent -> ProtectionStatus.PAUSED
        activeSources == 0 -> ProtectionStatus.ATTENTION
        preferences.enabled.any { (it == ProtectionPermission.SMS || it == ProtectionPermission.CALLS || it == ProtectionPermission.NOTIFICATIONS) && it !in granted } -> ProtectionStatus.ATTENTION
        ProtectionPermission.NOTIFICATIONS in preferences.enabled && preferences.allowedPackages.isEmpty() -> ProtectionStatus.ATTENTION
        !demo && (!online || !backendReady || !backendAvailable || !preferences.cloudConsent) -> ProtectionStatus.ATTENTION
        ProtectionPermission.WARNINGS !in granted || ProtectionPermission.WARNINGS !in preferences.enabled ||
            revoked.isNotEmpty() || preferences.lastCheckFailed -> ProtectionStatus.ATTENTION
        else -> ProtectionStatus.PROTECTED
    }
}

fun Verdict.needsWarning(): Boolean = when (this) {
    Verdict.CAUTION, Verdict.HIGH_RISK, Verdict.CONFIRMED_FRAUD -> true
    Verdict.VERIFIED, Verdict.SAFE -> false
}
