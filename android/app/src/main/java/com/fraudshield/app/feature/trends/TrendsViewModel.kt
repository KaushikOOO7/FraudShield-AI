package com.fraudshield.app.feature.trends

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.FraudRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel class TrendsViewModel @Inject constructor(private val repository: FraudRepository): ViewModel() {
    private val mutable = MutableStateFlow<UiState<Trends>>(UiState.Loading); val state = mutable.asStateFlow()
    private val mutableRange = MutableStateFlow("7d"); val range = mutableRange.asStateFlow()
    init { retry() }
    fun range(value: String) { mutableRange.value = value; retry() }
    fun retry() { viewModelScope.launch { mutable.value = UiState.Loading
        runCatching { repository.trends(range.value) }.onSuccess { mutable.value = if (it.totalScanned == 0 && it.weekly.isEmpty()) UiState.Empty else UiState.Data(it) }
            .onFailure { mutable.value = it.toUiError() }
    } }
}
