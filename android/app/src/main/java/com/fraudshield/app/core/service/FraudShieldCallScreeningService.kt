package com.fraudshield.app.core.service

import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService
import android.util.Log
import com.fraudshield.app.core.model.ManualCheck
import com.fraudshield.app.data.monitoring.SignalCoordinator
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.*

@AndroidEntryPoint
class FraudShieldCallScreeningService : CallScreeningService() {
    @Inject lateinit var coordinator: SignalCoordinator
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate + CoroutineExceptionHandler { _, error ->
        Log.w("FraudShield", "Caller intake failed: ${error.javaClass.simpleName}")
    })
    override fun onScreenCall(details: Call.Details) {
        if (Build.VERSION.SDK_INT >= 29 && details.callDirection != Call.Details.DIRECTION_INCOMING) return
        // Meet Android's screening deadline immediately. Version 1 never blocks a call.
        try {
            respondToCall(details, CallResponse.Builder().setDisallowCall(false).setRejectCall(false)
                .setSkipCallLog(false).setSkipNotification(false).build())
        } catch (error: SecurityException) {
            Log.w("FraudShield", "Call role changed: ${error.javaClass.simpleName}"); return
        }
        if (Build.VERSION.SDK_INT < 29 || !coordinator.acceptsCaller()) return
        val number = details.handle?.schemeSpecificPart ?: return
        val phone = try { ManualCheck.phone(number) } catch (_: IllegalArgumentException) { return }
        scope.launch { coordinator.caller(phone) }
    }
    override fun onDestroy() { scope.cancel(); super.onDestroy() }
}
