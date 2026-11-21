package com.fraudshield.app.feature.scan

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.PickVisualMediaRequest
import com.fraudshield.app.core.model.ProtectionPermission
import coil.compose.AsyncImage
import coil.request.ImageRequest
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ScanRoute(locale: String, onCase: (String) -> Unit) {
    val model: ScanViewModel = hiltViewModel()
    val tab by model.tab.collectAsStateWithLifecycle()
    val input by model.input.collectAsStateWithLifecycle()
    val result by model.result.collectAsStateWithLifecycle()
    val consent by model.consent.collectAsStateWithLifecycle()
    val country by model.country.collectAsStateWithLifecycle()
    var countryMenu by remember { mutableStateOf(false) }
    val health by model.permissionHealth.collectAsStateWithLifecycle()
    val screenshot by model.screenshot.collectAsStateWithLifecycle()
    val photoPicker=rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()){model.screenshot(it)}
    val cameraPermission=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()){model.refreshPermissions()}
    val context=LocalContext.current
    val caseToOpen by model.caseToOpen.collectAsStateWithLifecycle()
    LaunchedEffect(caseToOpen) { caseToOpen?.let { onCase(it); model.consumeCase() } }
    val tabs = listOf("text" to R.string.tab_text, "qr" to R.string.tab_qr,
        "call" to R.string.tab_call, "screenshot" to R.string.tab_screenshot)
    ScreenList {
        item {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                tabs.forEach { (id, label) ->
                    FilterChip(tab == id, { model.selectTab(id) }, { Text(stringResource(label)) }, modifier = Modifier.heightIn(min = 48.dp))
                }
            }
        }
        item {
            ShieldCard {
                when (tab) {
                    "qr" -> {
                        if(input.isBlank()&&ProtectionPermission.CAMERA in health.granted)
                            QrCamera(Modifier.fillMaxWidth().height(280.dp),model::qr,model::cameraError)
                        else if(ProtectionPermission.CAMERA !in health.granted){Text(stringResource(R.string.permission_camera_why));SecondaryButton(stringResource(R.string.enable_camera),{cameraPermission.launch(android.Manifest.permission.CAMERA)})}
                        OutlinedTextField(input,model::input,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.qr_content))})
                        if(input.isNotBlank())SecondaryButton(stringResource(R.string.scan_again),{model.input("")})
                    }
                    "screenshot" -> {
                        Text(stringResource(R.string.screenshot_consent))
                        SecondaryButton(stringResource(R.string.pick_screenshot),{photoPicker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))})
                        screenshot?.let{uri->AsyncImage(model=ImageRequest.Builder(context).data(uri).size(1024).build(),contentDescription=stringResource(R.string.screenshot_preview),modifier=Modifier.fillMaxWidth().height(220.dp))}
                        if(!model.evidenceReady&&!model.isDemo)Notice(stringResource(R.string.upload_pending),true)
                    }
                    "call" -> {
                        Box {
                            SecondaryButton(stringResource(R.string.country_code, country), { countryMenu = true })
                            DropdownMenu(countryMenu, { countryMenu = false }) {
                                listOf("+91", "+1", "+44", "+971").forEach { code ->
                                    DropdownMenuItem({ Text(code) }, { model.country(code); countryMenu = false })
                                }
                            }
                        }
                        OutlinedTextField(input, model::input, Modifier.fillMaxWidth(),
                            label = { Text(stringResource(R.string.number_label)) }, singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone))
                    }
                    else -> OutlinedTextField(input, model::input, Modifier.fillMaxWidth(),
                        label = { Text(stringResource(R.string.paste_label)) }, minLines = 4)
                }
                Notice(stringResource(if (model.isDemo) R.string.demo_check_explanation else R.string.manual_consent_body))
                val consentLabel = stringResource(if (model.isDemo) R.string.demo_consent else R.string.manual_consent_label)
                Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Checkbox(consent, model::consent, Modifier.semantics { contentDescription = consentLabel })
                    Text(consentLabel, Modifier.weight(1f))
                }
                if (!model.isDemo && !model.backendReady) Notice(stringResource(R.string.backend_pending), caution = true)
                PrimaryButton(stringResource(if (model.isDemo) R.string.check_demo else R.string.check_now), { model.check(locale) },
                    enabled = consent && (model.isDemo || model.backendReady) &&
                        (tab!="screenshot"||model.isDemo||(screenshot!=null&&model.evidenceReady)))
            }
        }
        item {
            StateContent(result, stringResource(R.string.no_check_yet), stringResource(R.string.manual_check_scope), { model.check(locale) }) { case ->
                CaseSummary(case) { onCase(case.caseId) }
            }
        }
    }
}
