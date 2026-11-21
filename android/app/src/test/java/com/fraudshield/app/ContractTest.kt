package com.fraudshield.app

import com.fraudshield.app.core.model.*
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ContractTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun fixtureCasesCoverExactVerdictEnumsAndValidScores() {
        val cases = loadCases()
        assertEquals(Verdict.entries.toSet(), cases.map { it.verdict }.toSet())
        assertTrue(cases.all { it.caseId.startsWith("DEMO-") })
        assertTrue(cases.all { it.riskScore in 0..100 && it.confidence in 0.0..1.0 })
        assertTrue(cases.any { it.agentFindings.any { finding -> finding.signals.isNotEmpty() } })
    }

    @Test(expected = SerializationException::class)
    fun unknownVerdictCannotBecomeAnInventedSafeResult() {
        json.decodeFromString<Investigation>("""{"case_id":"FS-test","verdict":"UNKNOWN","risk_score":4,"confidence":0.8}""")
    }

    @Test(expected = IllegalArgumentException::class)
    fun outOfRangeBackendScoreIsRejected() {
        json.decodeFromString<Investigation>("""{"case_id":"FS-test","verdict":"CAUTION","risk_score":101,"confidence":0.8}""")
    }

    @Test
    fun partialErrorsKeepCodeAndRetryability() {
        val parsed = json.decodeFromString<ApiErrorEnvelope>("""{"error":{"code":"MODEL_UNAVAILABLE","message":"Try later","retryable":true}}""")
        assertEquals("MODEL_UNAVAILABLE", parsed.error.code)
        assertTrue(parsed.error.retryable)
    }

    private fun loadCases(): List<Investigation> {
        val stream = requireNotNull(javaClass.classLoader?.getResourceAsStream("demo/cases.json"))
        return stream.bufferedReader().use { json.decodeFromString(it.readText()) }
    }
}
