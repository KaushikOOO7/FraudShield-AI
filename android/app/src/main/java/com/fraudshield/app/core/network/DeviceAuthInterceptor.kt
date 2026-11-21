package com.fraudshield.app.core.network

import okhttp3.Interceptor
import okhttp3.Response

interface DeviceTokenProvider { fun token(): String? }

class DeviceAuthInterceptor(private val tokens: DeviceTokenProvider) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val token = tokens.token()
        val registration = original.url.encodedPath.endsWith("/api/v1/device/register")
        val request = if (registration || token == null) original
            else original.newBuilder().header("Authorization", "Bearer $token").build()
        return chain.proceed(request)
    }
}
