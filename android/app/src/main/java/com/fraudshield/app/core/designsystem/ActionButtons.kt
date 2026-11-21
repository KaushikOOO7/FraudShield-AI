package com.fraudshield.app.core.designsystem

import android.content.ActivityNotFoundException
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import com.fraudshield.app.BuildConfig
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.ActionType
import com.fraudshield.app.core.model.Investigation
import com.fraudshield.app.core.model.CaseAction

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ActionButtons(actions:List<CaseAction>, contextLabel:String, caseId:String?=null) {
    val context = LocalContext.current
    var sheet by remember { mutableStateOf<ActionType?>(null) }
    var failed by remember { mutableStateOf(false) }
    val sharedWarning = stringResource(R.string.share_warning_text, contextLabel, caseId ?: context.getString(R.string.information))
    actions.forEach { action ->
        when (action.type) {
            ActionType.NONE -> Text(action.label, color = ShieldColors.TextMid)
            else -> PrimaryButton(action.label, {
                when (action.type) {
                    ActionType.CALL_1930 -> failed = !openExternal(context, "tel:1930")
                    ActionType.REPORT_NCRP -> failed = !openExternal(context, "https://cybercrime.gov.in/")
                    ActionType.FREEZE_BANK, ActionType.BLOCK_SENDER -> sheet = action.type
                    ActionType.SHARE_WARNING -> try {
                        val prefix = if (BuildConfig.DEBUG && BuildConfig.DEMO_MODE) "DEMO · " else ""
                        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain")
                            .putExtra(Intent.EXTRA_TEXT, prefix + sharedWarning), context.getString(R.string.share_warning)))
                    } catch (error: ActivityNotFoundException) {
                        Log.w("FraudShield", "Share unavailable: ${error.javaClass.simpleName}"); failed = true
                    } catch (error: SecurityException) {
                        Log.w("FraudShield", "Share denied: ${error.javaClass.simpleName}"); failed = true
                    }
                    ActionType.NONE -> Unit
                }
            })
        }
    }
    if (failed) Notice(stringResource(R.string.external_action_failed), caution = true)
    sheet?.let { type ->
        ModalBottomSheet(onDismissRequest = { sheet = null }) {
            ScreenList {
                item { Notice(stringResource(if (type == ActionType.FREEZE_BANK) R.string.freeze_sheet_explanation else R.string.block_sender_explanation)) }
                if (type == ActionType.FREEZE_BANK) {
                    listOf("SBI YONO" to "com.sbi.lotusintouch", "HDFC Bank" to "com.snapwork.hdfc",
                        "ICICI iMobile" to "com.csam.icici.bank.imobile", "Axis Mobile" to "com.axis.mobile").forEach { (label, packageName) ->
                        item { SecondaryButton(label, {
                            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
                            if (intent == null) failed = true else try { context.startActivity(intent); sheet = null }
                            catch (error: ActivityNotFoundException) { Log.w("FraudShield", "Bank app unavailable: ${error.javaClass.simpleName}"); failed = true }
                            catch (error: SecurityException) { Log.w("FraudShield", "Bank app denied: ${error.javaClass.simpleName}"); failed = true }
                        }) }
                    }
                } else item { SecondaryButton(stringResource(R.string.open_messages_app), {
                    val packageName = Telephony.Sms.getDefaultSmsPackage(context)
                    val intent = packageName?.let { context.packageManager.getLaunchIntentForPackage(it) }
                    if (intent == null) failed = true else try { context.startActivity(intent); sheet = null }
                    catch (error: ActivityNotFoundException) { Log.w("FraudShield", "SMS app unavailable: ${error.javaClass.simpleName}"); failed = true }
                    catch (error: SecurityException) { Log.w("FraudShield", "SMS app denied: ${error.javaClass.simpleName}"); failed = true }
                }) }
                if (failed) item { Notice(stringResource(R.string.bank_app_fallback), caution = true) }
                item { SecondaryButton(stringResource(R.string.close), { sheet = null }) }
            }
        }
    }
}
