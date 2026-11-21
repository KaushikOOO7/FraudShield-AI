package com.fraudshield.app

import com.fraudshield.app.core.model.*
import org.junit.Assert.*
import org.junit.Test

class SignalPolicyTest {
    private val consented = ProtectionPreferences(monitoring = true, monitoringConsent = true, cloudConsent = true,
        enabled = setOf(ProtectionPermission.NOTIFICATIONS, ProtectionPermission.WARNINGS), allowedPackages = setOf("allowed.app"))
    @Test fun prefilterFindsKeywordsButDoesNotClassifyOrdinaryText() {
        assertTrue(SignalPolicy.matches("Urgent KYC: account blocked"))
        assertTrue(SignalPolicy.matches("केवाईसी के लिए ओटीपी"))
        assertTrue(SignalPolicy.matches("ಒಟಿಪಿ ಕೇಳಿದ್ದಾರೆ"))
        assertFalse(SignalPolicy.matches("Lunch is ready"))
    }
    @Test fun consentGrantAndSourceAreEachRequired() {
        assertTrue(SignalPolicy.allowed(consented, ProtectionPermission.NOTIFICATIONS, true))
        assertFalse(SignalPolicy.allowed(consented, ProtectionPermission.NOTIFICATIONS, false))
        assertFalse(SignalPolicy.allowed(consented.copy(monitoringConsent = false), ProtectionPermission.NOTIFICATIONS, true))
        assertFalse(SignalPolicy.allowed(consented.copy(monitoring = false), ProtectionPermission.NOTIFICATIONS, true))
        assertFalse(SignalPolicy.allowed(consented.copy(cloudConsent = false), ProtectionPermission.NOTIFICATIONS, true))
        assertFalse(SignalPolicy.allowed(consented, ProtectionPermission.SMS, true))
    }
    @Test fun sourceDebounceExpiresAtTenMinutesAndIsIndependentAcrossSources() {
        val debounce = SourceDebouncer()
        assertTrue(debounce.accept("source-A", 1000))
        assertFalse(debounce.accept("source-A", 2000))
        assertTrue(debounce.accept("source-B", 2000))
        assertTrue(debounce.accept("source-A", 601000))
    }
    @Test fun onlyAttentionVerdictsTriggerWarningNotifications() {
        assertFalse(Verdict.VERIFIED.needsWarning())
        assertFalse(Verdict.SAFE.needsWarning())
        assertTrue(Verdict.CAUTION.needsWarning())
        assertTrue(Verdict.HIGH_RISK.needsWarning())
        assertTrue(Verdict.CONFIRMED_FRAUD.needsWarning())
    }
    @Test fun deniedOrRevokedPermissionsCannotAppearProtected() {
        val health = PermissionHealth(granted = consented.enabled, online = true, preferences = consented, backendReady = true, backendAvailable = true)
        assertEquals(ProtectionStatus.PROTECTED, health.status)
        assertEquals(ProtectionStatus.ATTENTION, health.copy(granted = setOf(ProtectionPermission.WARNINGS)).status)
        assertEquals(ProtectionStatus.ATTENTION, health.copy(online = false).status)
        assertEquals(ProtectionStatus.ATTENTION, health.copy(backendAvailable = false).status)
        assertEquals(ProtectionStatus.PAUSED, health.copy(preferences = consented.copy(monitoring = false)).status)
        assertEquals(ProtectionStatus.ATTENTION, health.copy(preferences = consented.copy(allowedPackages = emptySet())).status)
    }
}
