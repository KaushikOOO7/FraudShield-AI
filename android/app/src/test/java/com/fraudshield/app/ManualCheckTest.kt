package com.fraudshield.app

import com.fraudshield.app.core.model.ManualCheck
import com.fraudshield.app.core.model.SignalType
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.*
import org.junit.Test

class ManualCheckTest {
    @Test fun wholeLinkAndMessageContainingLinkAreDifferentInputs() {
        val link = ManualCheck.request("https://example.invalid/kyc", false, "en")
        val message = ManualCheck.request("Urgent KYC: visit https://example.invalid/kyc", false, "hi")
        assertEquals(SignalType.URL, link.type)
        assertEquals(SignalType.SMS, message.type)
        assertEquals("hi", message.locale)
        assertTrue(link.clientTs.endsWith("Z"))
    }
    @Test fun bareDomainGetsAnHttpsScheme() {
        val request = ManualCheck.request("example.org", false, "kn")
        assertEquals("https://example.org", request.payload["url"]?.jsonPrimitive?.content)
    }
    @Test fun indianMobileNumberGetsCountryCodeAndIncomingE164IsPreserved() {
        assertEquals("+919876543210", ManualCheck.phone("98765 43210"))
        assertEquals("+442071234567", ManualCheck.phone("+44 20 7123 4567"))
    }
    @Test fun otpDigitsAreRedactedWithoutLosingTheRequestSignal() {
        val request = ManualCheck.request("OTP: 123456. Urgent KYC request", false, "en")
        val text = request.payload["text"]?.jsonPrimitive?.content.orEmpty()
        assertFalse(text.contains("123456"))
        assertTrue(text.contains("OTP"))
        assertTrue(text.contains("KYC"))
    }
    @Test(expected = IllegalArgumentException::class) fun emptyInputCannotProduceAVerdict() { ManualCheck.request("  ", false, "en") }
    @Test(expected = IllegalArgumentException::class) fun invalidCallerIsRejected() { ManualCheck.request("bank helpline", true, "en") }
    @Test(expected = IllegalArgumentException::class) fun urlWithCredentialsIsRejected() { ManualCheck.request("https://user:secret@example.org", false, "en") }
}
