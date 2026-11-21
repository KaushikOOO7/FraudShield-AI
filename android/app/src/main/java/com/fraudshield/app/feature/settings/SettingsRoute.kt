package com.fraudshield.app.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import com.fraudshield.app.core.model.ProtectionPermission
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.fraudshield.app.BuildConfig
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SettingsRoute(locale: String, onLocale: (String) -> Unit, onNavigate: (String) -> Unit) {
    val model: SettingsViewModel = hiltViewModel()
    val health by model.health.collectAsStateWithLifecycle()
    val backgroundLabel = stringResource(R.string.background_checks)
    val counts by model.counts.collectAsStateWithLifecycle();val operation by model.operation.collectAsStateWithLifecycle();val export by model.export.collectAsStateWithLifecycle()
    var confirmDelete by remember{mutableStateOf(false)};var shareFailed by remember{mutableStateOf(false)}
    val context=LocalContext.current
    LaunchedEffect(export){export?.let{file->try{shareFile(context,file,"application/json")}catch(failure:android.content.ActivityNotFoundException){android.util.Log.w("FraudShield","Export share unavailable");shareFailed=true}finally{model.consumeExport()}}}
    ScreenList {
        if(shareFailed)item{Notice(stringResource(R.string.error_generic),true)}
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.protection_controls))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(R.string.background_checks), Modifier.weight(1f))
                    Switch(health.preferences.monitoring, model::monitoring, modifier = Modifier.heightIn(min = 48.dp)
                        .semantics { contentDescription = backgroundLabel }, enabled = health.preferences.monitoringConsent)
                }
                health.preferences.enabled.forEach { permission ->
                    val label = when (permission) {
                        ProtectionPermission.NOTIFICATIONS -> R.string.permission_notifications
                        ProtectionPermission.CALLS -> R.string.permission_calls
                        ProtectionPermission.SMS -> R.string.permission_sms
                        ProtectionPermission.WARNINGS -> R.string.permission_warnings
                        ProtectionPermission.CAMERA -> R.string.permission_camera
                        ProtectionPermission.CONTACTS -> R.string.permission_contacts
                    }
                    Text(stringResource(label) + " · " + stringResource(if (permission in health.granted) R.string.permission_granted else R.string.not_enabled),
                        color = if (permission in health.granted) ShieldColors.Safe else ShieldColors.Caution)
                }
                SecondaryButton(stringResource(R.string.review_permissions), { onNavigate("permissions") })
                SecondaryButton(stringResource(R.string.withdraw_monitoring_consent), model::withdraw)
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.choose_language))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("en" to "English", "hi" to "हिन्दी", "kn" to "ಕನ್ನಡ").forEach { (code, label) ->
                        FilterChip(locale == code, { onLocale(code) }, { Text(label) }, modifier = Modifier.heightIn(min = 48.dp))
                    }
                }
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.privacy_center))
                Text(stringResource(R.string.privacy_promise))
                StateContent(counts,stringResource(R.string.nothing_here),stringResource(R.string.privacy_center),{}){value->
                    Text(stringResource(R.string.stored_counts,value.cases,value.queuedReports,value.settings))}
                SecondaryButton(stringResource(R.string.export_data),model::export)
                PrimaryButton(stringResource(R.string.delete_data),{confirmDelete=true})
                StateContent(operation,stringResource(R.string.privacy_controls),stringResource(R.string.privacy_promise),{}){result->
                    Text(stringResource(if(result=="LOCAL_ONLY")R.string.local_deleted else if(BuildConfig.DEMO_MODE)R.string.demo_deleted else R.string.remote_deleted))}
                Notice(stringResource(R.string.legal_review))
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.methodology))
                Text(stringResource(R.string.methodology_body), color = ShieldColors.TextMid)
                Text(stringResource(R.string.legal_disclaimer), color = ShieldColors.TextMid)
                Text(stringResource(R.string.version_label, BuildConfig.VERSION_NAME))
                SecondaryButton(stringResource(R.string.about_intro), { onNavigate("welcome") })
            }
        }
    }
    if(confirmDelete)AlertDialog(onDismissRequest={confirmDelete=false},title={Text(stringResource(R.string.delete_data))},text={Text(stringResource(R.string.delete_explanation))},
        confirmButton={TextButton({confirmDelete=false;model.delete(model.canDeleteRemote)}){Text(stringResource(if(model.canDeleteRemote)R.string.delete_data else R.string.delete_local))}},
        dismissButton={TextButton({confirmDelete=false}){Text(stringResource(R.string.cancel))}})
}
