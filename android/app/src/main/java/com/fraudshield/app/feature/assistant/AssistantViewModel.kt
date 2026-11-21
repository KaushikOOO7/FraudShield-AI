package com.fraudshield.app.feature.assistant

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.*
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ChatMessage(val text: String,val user: Boolean)
@HiltViewModel class AssistantViewModel @Inject constructor(private val repository: FraudRepository,
    private val preferences: PreferencesRepository, private val context: CaseContextStore): ViewModel() {
    private val mutableMessages = MutableStateFlow<List<ChatMessage>>(emptyList()); val messages=mutableMessages.asStateFlow()
    val caseId=context.caseId
    fun clearCase(){context.select(null)}
    private val mutable = MutableStateFlow<UiState<AssistantAnswer>>(UiState.Empty); val state=mutable.asStateFlow()
    private val mutableInput=MutableStateFlow(""); val input=mutableInput.asStateFlow()
    private val mutableConsent=MutableStateFlow(false); val consent=mutableConsent.asStateFlow()
    fun input(value:String) { mutableInput.value=value; mutableConsent.value=false }
    fun consent(value:Boolean) { mutableConsent.value=value }
    fun send() {
        if (input.value.isBlank() || !consent.value || state.value==UiState.Loading) return
        val question=ManualCheck.redactOtp(input.value.take(4000)); preferences.cloudConsent()
        mutableMessages.value=messages.value+ChatMessage(question,true); mutableInput.value=""; mutableConsent.value=false
        viewModelScope.launch { mutable.value=UiState.Loading
            runCatching { repository.assistant(AssistantRequest(question,context.caseId.value)) }
                .onSuccess { mutableMessages.value=messages.value+ChatMessage(it.answer,false); mutable.value=UiState.Data(it) }
                .onFailure { mutable.value=it.toUiError() }
        }
    }
    fun retry() { messages.value.lastOrNull { it.user }?.let { mutableInput.value=it.text; mutableConsent.value=true; send() } }
}
