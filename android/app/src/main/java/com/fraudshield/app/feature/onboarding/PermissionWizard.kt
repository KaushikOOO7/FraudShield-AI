package com.fraudshield.app.feature.onboarding

import android.Manifest
import android.app.role.RoleManager
import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.ProtectionPermission
import com.fraudshield.app.core.service.FraudShieldListener

@Composable
internal fun PermissionWizard(onHome: () -> Unit) {
    val model: PermissionsViewModel = hiltViewModel()
    val health by model.health.collectAsStateWithLifecycle()
    val error by model.error.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val backgroundLabel = stringResource(R.string.background_checks)
    val owner = LocalLifecycleOwner.current
    val settingsLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { model.refresh() }
    val runtimeLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { model.refresh() }
    DisposableEffect(owner, model) {
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_RESUME) model.refresh() }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    val open: (ProtectionPermission, Boolean) -> Unit = { permission, settingsOnly ->
        try {
            if (settingsOnly) {
                settingsLauncher.launch(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${context.packageName}")))
            } else when (permission) {
                ProtectionPermission.NOTIFICATIONS -> {
                    val intent = if (Build.VERSION.SDK_INT >= 30) Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS)
                        .putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME, ComponentName(context, FraudShieldListener::class.java).flattenToString())
                        else Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                    settingsLauncher.launch(intent)
                }
                ProtectionPermission.CALLS -> if (Build.VERSION.SDK_INT >= 29) {
                    context.getSystemService(RoleManager::class.java)?.let { settingsLauncher.launch(it.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING)) }
                }
                ProtectionPermission.SMS -> runtimeLauncher.launch(Manifest.permission.RECEIVE_SMS)
                ProtectionPermission.WARNINGS -> if (Build.VERSION.SDK_INT >= 33) runtimeLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                    else settingsLauncher.launch(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName))
                ProtectionPermission.CAMERA -> runtimeLauncher.launch(Manifest.permission.CAMERA)
                ProtectionPermission.CONTACTS -> runtimeLauncher.launch(Manifest.permission.READ_CONTACTS)
            }
        } catch (failure: ActivityNotFoundException) {
            Log.w("FraudShield", "Permission settings unavailable: ${failure.javaClass.simpleName}"); model.actionFailed()
        } catch (failure: SecurityException) {
            Log.w("FraudShield", "Permission settings denied: ${failure.javaClass.simpleName}"); model.actionFailed()
        }
    }
    val cards = listOf(
        Triple(ProtectionPermission.NOTIFICATIONS, R.string.permission_notifications, R.string.permission_notifications_why),
        Triple(ProtectionPermission.CALLS, R.string.permission_calls, R.string.permission_calls_why),
        Triple(ProtectionPermission.SMS, R.string.permission_sms, R.string.permission_sms_why),
        Triple(ProtectionPermission.WARNINGS, R.string.permission_warnings, R.string.permission_warnings_why),
        Triple(ProtectionPermission.CAMERA, R.string.permission_camera, R.string.permission_camera_why),
        Triple(ProtectionPermission.CONTACTS, R.string.permission_contacts, R.string.permission_contacts_why),
    )
    ScreenList {
        item { Notice(stringResource(R.string.permission_control)) }
        error?.let { message -> item { Notice(message, caution = true); SecondaryButton(stringResource(R.string.retry), model::refresh) } }
        item {
            ShieldCard {
                Text(stringResource(R.string.monitoring_consent_title), style = MaterialTheme.typography.titleLarge)
                Text(stringResource(R.string.monitoring_consent_body), color = ShieldColors.TextMid)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(R.string.background_checks), Modifier.weight(1f))
                    Switch(health.preferences.monitoringConsent, model::consent,
                        modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = backgroundLabel })
                }
                if (!health.demo && !health.backendReady) Notice(stringResource(R.string.backend_pending))
            }
        }
        cards.forEach { (permission, title, why) -> item {
            val supported = permission in health.supported
            val granted = permission in health.granted
            val permissionLabel = stringResource(title)
            ShieldCard {
                Text(stringResource(title), style = MaterialTheme.typography.titleLarge)
                SectionLabel(stringResource(R.string.why_permission))
                Text(stringResource(why), color = ShieldColors.TextMid)
                Text(stringResource(if (!supported) R.string.permission_unsupported else if (granted) R.string.permission_granted else R.string.not_enabled),
                    color = if (granted) ShieldColors.Safe else ShieldColors.Caution)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(R.string.use_this_source), Modifier.weight(1f))
                    Switch(permission in health.preferences.enabled,
                        { enabled -> model.permission(permission, enabled); if (enabled && !granted) open(permission, false) },
                        modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = permissionLabel },
                        enabled = supported && (health.preferences.monitoringConsent || permission == ProtectionPermission.CAMERA || permission == ProtectionPermission.CONTACTS || permission == ProtectionPermission.WARNINGS))
                }
                SecondaryButton(stringResource(R.string.open_settings), { open(permission, false) }, supported)
                SecondaryButton(stringResource(R.string.app_settings), { open(permission, true) })
                if (permission == ProtectionPermission.NOTIFICATIONS) {
                    SectionLabel(stringResource(R.string.allowed_notification_apps))
                    if (health.availableApps.isEmpty()) Text(stringResource(R.string.no_supported_apps), color = ShieldColors.TextMid)
                    health.availableApps.forEach { app ->
                        val description = stringResource(R.string.allow_app_notifications, app.label)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(app.label, Modifier.weight(1f))
                            Switch(app.packageName in health.preferences.allowedPackages,
                                { model.allow(app.packageName, it) }, modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = description },
                                enabled = health.preferences.monitoringConsent)
                        }
                    }
                }
            }
        } }
        item { PrimaryButton(stringResource(R.string.finish_permissions), { model.finish(); onHome() }) }
        item { SecondaryButton(stringResource(R.string.skip_for_now), { model.finish(); onHome() }) }
    }
}
