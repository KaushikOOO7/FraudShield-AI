package com.fraudshield.app.feature.scan

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.FraudRepository
import com.fraudshield.app.data.repository.PreferencesRepository
import com.fraudshield.app.data.repository.ClientDataRepository
import com.fraudshield.app.data.repository.PermissionHealthRepository
import android.net.Uri
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.Instant
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

@HiltViewModel
class ScanViewModel @Inject constructor(
    private val repository: FraudRepository,
    private val savedStateHandle: SavedStateHandle,
    private val preferences: PreferencesRepository,
    private val data:ClientDataRepository,
    private val permissions:PermissionHealthRepository,
) : ViewModel() {
    val isDemo: Boolean = repository.isDemo
    val tab = savedStateHandle.getStateFlow("tab", "text")
    val input = savedStateHandle.getStateFlow("input", "")
    val consent = savedStateHandle.getStateFlow("consent", false)
    val country = savedStateHandle.getStateFlow("country", "+91")
    val permissionHealth=permissions.health
    private val mutableScreenshot=MutableStateFlow<Uri?>(null);val screenshot=mutableScreenshot.asStateFlow()
    val evidenceReady get()=data.evidenceReady
    fun screenshot(uri:Uri?){mutableScreenshot.value=uri;savedStateHandle["consent"]=false}
    fun qr(value:String){savedStateHandle["input"]=value;savedStateHandle["consent"]=false}
    fun cameraError(){mutableResult.value=UiState.Error("Camera unavailable. Paste the QR content instead.",true,"INPUT")}
    fun refreshPermissions(){viewModelScope.launch{runCatching{permissions.refresh()}.onFailure{it.toUiError()}}}
    val backendReady: Boolean get() = com.fraudshield.app.BuildConfig.BACKEND_READY
    private val mutableResult = MutableStateFlow<UiState<Investigation>>(UiState.Empty)
    val result = mutableResult.asStateFlow()
    private val mutableCaseToOpen = MutableStateFlow<String?>(null)
    val caseToOpen = mutableCaseToOpen.asStateFlow()
    private var job: Job? = null

    fun selectTab(value: String) {
        job?.cancel()
        savedStateHandle["tab"] = value
        mutableResult.value = UiState.Empty
        savedStateHandle["consent"] = false
    }
    fun input(value: String) { job?.cancel(); savedStateHandle["input"] = value; savedStateHandle["consent"] = false; mutableResult.value = UiState.Empty }
    fun consent(enabled: Boolean) { savedStateHandle["consent"] = enabled }
    fun country(code: String) { savedStateHandle["country"] = code; savedStateHandle["consent"] = false }
    fun consumeCase() { mutableCaseToOpen.value = null }

    fun check(locale: String) {
        if (!consent.value) {
            mutableResult.value = UiState.Error("Choose whether to send this content for a check first.", false, "CONSENT_REQUIRED")
            return
        }
        job?.cancel()
        job = viewModelScope.launch {
            mutableResult.value = UiState.Loading
            val request = try {
                if (repository.isDemo && (tab.value == "qr" || tab.value == "screenshot")) {
                    AnalyzeRequest(if (tab.value == "qr") SignalType.QR else SignalType.SCREENSHOT,
                        buildJsonObject { put("demo", true) }, locale, Instant.now().toString())
                } else if(tab.value=="qr") {
                    require(input.value.isNotBlank())
                    AnalyzeRequest(SignalType.QR,buildJsonObject{put("text",input.value)},locale,Instant.now().toString())
                } else if(tab.value=="screenshot") {
                    AnalyzeRequest(SignalType.SCREENSHOT,buildJsonObject{},locale,Instant.now().toString())
                } else {
                    val value = if (tab.value == "call" && !input.value.trim().startsWith("+")) country.value + input.value.trim() else input.value
                    ManualCheck.request(value, tab.value == "call", locale)
                }
            } catch (error: IllegalArgumentException) {
                error.toUiError()
                mutableResult.value = UiState.Error(error.message ?: "Check your input.", false, "INPUT")
                return@launch
            } catch (error: java.net.URISyntaxException) {
                error.toUiError()
                mutableResult.value = UiState.Error("Enter a valid web link without spaces or credentials.", false, "INPUT")
                return@launch
            }
            runCatching {
                preferences.cloudConsent()
                val prepared=if(tab.value=="screenshot"&&!repository.isDemo){
                    val ref=data.upload(requireNotNull(screenshot.value))
                    request.copy(payload=buildJsonObject{put("evidence_ref",ref)})
                }else request
                repository.analyze(prepared)
            }.onSuccess {
                    mutableResult.value = UiState.Data(it)
                    mutableCaseToOpen.value = it.caseId
                    preferences.checkFailed(false)
                    savedStateHandle["consent"] = false
                }
                .onFailure { mutableResult.value = it.toUiError() }
        }
    }
}
