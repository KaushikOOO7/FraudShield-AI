package com.fraudshield.app

import com.fraudshield.app.core.model.ManualCheck
import com.fraudshield.app.core.model.AnalyzeRequest
import com.fraudshield.app.core.network.DeviceAuthInterceptor
import com.fraudshield.app.core.network.DeviceTokenProvider
import com.fraudshield.app.data.api.FraudShieldApi
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

class NetworkContractTest {
    @Test fun registrationHasNoBearerHeaderButAnalyzeUsesAnonymousDeviceToken() = runTest {
        val server = MockWebServer()
        server.start()
        try {
            var token: String? = null
            val provider = object : DeviceTokenProvider { override fun token(): String? = token }
            val json = Json { ignoreUnknownKeys = true }
            val api = Retrofit.Builder().baseUrl(server.url("/"))
                .client(OkHttpClient.Builder().addInterceptor(DeviceAuthInterceptor(provider)).build())
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType())).build()
                .create(FraudShieldApi::class.java)
            server.enqueue(MockResponse().setBody("""{"device_token":"test-device-token"}"""))
            token = api.register(buildJsonObject {}).deviceToken
            val registration = requireNotNull(server.takeRequest(2, TimeUnit.SECONDS))
            assertEquals("/api/v1/device/register", registration.path)
            assertNull(registration.getHeader("Authorization"))
            val cases = requireNotNull(javaClass.classLoader?.getResourceAsStream("demo/cases.json"))
                .bufferedReader().use { json.parseToJsonElement(it.readText()) }
            val fixture = (cases as kotlinx.serialization.json.JsonArray).first().toString()
            server.enqueue(MockResponse().setBody(fixture))
            val result = api.analyze(ManualCheck.request("Urgent KYC request", false, "en"))
            val analyze = requireNotNull(server.takeRequest(2, TimeUnit.SECONDS))
            assertEquals("Bearer test-device-token", analyze.getHeader("Authorization"))
            assertEquals("/api/v1/analyze", analyze.path)
            val body = json.parseToJsonElement(analyze.body.readUtf8()).jsonObject
            assertEquals(setOf("type", "payload", "locale", "client_ts"), body.keys)
            assertEquals("sms", body["type"]?.jsonPrimitive?.content)
            assertEquals("DEMO-KYC", result.caseId)
        } finally { server.shutdown() }
    }
}
