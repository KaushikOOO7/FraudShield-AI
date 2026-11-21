package com.fraudshield.app.core.designsystem

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log

/** ACTION_DIAL avoids CALL_PHONE permission and lets the user confirm the call. */
fun openExternal(context: Context, uri: String): Boolean {
    val parsed = Uri.parse(uri)
    val intent = Intent(if (parsed.scheme == "tel") Intent.ACTION_DIAL else Intent.ACTION_VIEW, parsed)
    return try {
        context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        true
    } catch (error: ActivityNotFoundException) {
        Log.w("FraudShield", "No app available for external action: ${error.javaClass.simpleName}")
        false
    } catch (error: SecurityException) {
        Log.w("FraudShield", "External action denied: ${error.javaClass.simpleName}")
        false
    }
}
