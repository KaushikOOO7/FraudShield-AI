package com.fraudshield.app.feature.alerts

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.Investigation
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.model.FeedbackReceipt
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.FraudRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class AlertViewModel @Inject constructor(
    private val repository: FraudRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val caseId = savedStateHandle.get<String>("caseId")
    private val mutableState = MutableStateFlow<UiState<Investigation>>(UiState.Loading)
    val state = mutableState.asStateFlow()
    val canRefresh: Boolean get() = repository.canSync
    val canFeedback: Boolean get() = repository.canFeedback
    private val mutableFeedback = MutableStateFlow<UiState<FeedbackReceipt>>(UiState.Empty)
    val feedback = mutableFeedback.asStateFlow()
    private var job: Job? = null
    init { retry() }

    fun retry(fresh: Boolean = false) {
        job?.cancel()
        job = viewModelScope.launch {
            if (caseId.isNullOrBlank()) {
                mutableState.value = UiState.Empty
            } else {
                mutableState.value = UiState.Loading
                runCatching { if (fresh) repository.refreshCase(caseId) else repository.getCase(caseId) }
                    .onSuccess { mutableState.value = UiState.Data(it) }
                    .onFailure { mutableState.value = it.toUiError() }
            }
        }
    }
    fun markSafe() {
        if (caseId == null || !canFeedback || mutableFeedback.value == UiState.Loading) return
        viewModelScope.launch {
            mutableFeedback.value = UiState.Loading
            runCatching { repository.feedback(caseId) }.onSuccess { mutableFeedback.value = UiState.Data(it) }
                .onFailure { mutableFeedback.value = it.toUiError() }
        }
    }
}
