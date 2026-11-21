package com.fraudshield.app.core.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.fraudshield.app.data.monitoring.SignalCoordinator
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.*

@AndroidEntryPoint
class FraudShieldSmsReceiver : BroadcastReceiver() {
    @Inject lateinit var coordinator: SignalCoordinator
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        if (!coordinator.acceptsSms()) return
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) return
        val sender = messages.first().originatingAddress ?: "unknown"
        val text = messages.take(30).joinToString("") { it.messageBody.orEmpty() }.take(4000)
        val pending = goAsync()
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO + CoroutineExceptionHandler { _, error ->
            Log.w("FraudShield", "SMS intake failed: ${error.javaClass.simpleName}")
        })
        scope.launch {
            try { withTimeout(8_000) { coordinator.sms(sender, text) } }
            finally { pending.finish(); scope.cancel() }
        }
    }
}
