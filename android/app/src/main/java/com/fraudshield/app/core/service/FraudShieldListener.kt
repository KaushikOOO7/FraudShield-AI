package com.fraudshield.app.core.service

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.fraudshield.app.data.monitoring.SignalCoordinator
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.*

@AndroidEntryPoint
class FraudShieldListener : NotificationListenerService() {
    @Inject lateinit var coordinator: SignalCoordinator
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate + CoroutineExceptionHandler { _, error ->
        Log.w("FraudShield", "Notification intake failed: ${error.javaClass.simpleName}")
    })
    override fun onNotificationPosted(notification: StatusBarNotification?) {
        val item = notification ?: return
        if (!coordinator.acceptsNotification(item.packageName)) return
        if (item.packageName == packageName || item.notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        val text = try {
            val extras = item.notification.extras
            listOfNotNull(extras.getCharSequence(Notification.EXTRA_TITLE)?.take(1000),
                (extras.getCharSequence(Notification.EXTRA_BIG_TEXT) ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.take(3000))
                .joinToString("\n").take(4000)
        } catch (error: android.os.BadParcelableException) {
            Log.w("FraudShield", "Unsupported notification parcel: ${error.javaClass.simpleName}"); return
        } catch (error: ClassCastException) {
            Log.w("FraudShield", "Unsupported notification text: ${error.javaClass.simpleName}"); return
        }
        if (text.isNotBlank()) scope.launch { coordinator.notification(item.packageName, text) }
    }
    override fun onDestroy() { scope.cancel(); super.onDestroy() }
}
