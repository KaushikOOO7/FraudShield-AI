package com.fraudshield.app.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.Investigation
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.FraudRepository
import com.fraudshield.app.data.repository.PermissionHealthRepository
import com.fraudshield.app.core.model.PermissionHealth
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class HomeViewModel @Inject constructor(private val repository: FraudRepository,
    permissions: PermissionHealthRepository) : ViewModel() {
    val health = permissions.health
    val counts = cachedCountFlow()
    private val cachedCases = MutableStateFlow<UiState<List<Investigation>>>(UiState.Loading)
    private val refreshState = MutableStateFlow<UiState<Unit>>(UiState.Data(Unit))
    private var observation: Job? = null
    private var refresh: Job? = null
    val alerts = combine(cachedCases, refreshState) { cached, refreshing ->
        when (refreshing) {
            UiState.Loading -> UiState.Loading
            is UiState.Error -> refreshing
            else -> when (cached) {
                is UiState.Data -> if (cached.value.isEmpty()) UiState.Empty else UiState.Data(cached.value.take(2))
                is UiState.Error -> cached
                UiState.Empty -> UiState.Empty
                UiState.Loading -> UiState.Loading
            }
        }
    }.stateIn(viewModelScope, SharingStarted.Eagerly, UiState.Loading)

    init {
        observeCache()
        if (repository.canSync) retry()
    }

    fun retry() {
        refresh?.cancel()
        refresh = viewModelScope.launch {
            refreshState.value = UiState.Loading
            if (repository.canSync) {
                runCatching { repository.refreshHistory() }
                    .onSuccess { refreshState.value = UiState.Data(Unit) }
                    .onFailure { refreshState.value = it.toUiError() }
            } else {
                observeCache()
                refreshState.value = UiState.Data(Unit)
            }
        }
    }

    private fun cachedCountFlow() = repository.observeHistory().map { cases ->
        val count: UiState<Pair<Int, Int>> = UiState.Data(cases.size to cases.count { it.verdict != com.fraudshield.app.core.model.Verdict.SAFE })
        count
    }.catch { emit(it.toUiError()) }.stateIn(viewModelScope, SharingStarted.Eagerly, UiState.Loading)
    fun showSaved() { refresh?.cancel(); refreshState.value = UiState.Data(Unit); observeCache() }

    private fun observeCache() {
        observation?.cancel()
        observation = viewModelScope.launch {
            repository.observeHistory().catch { cachedCases.value = it.toUiError() }
                .collect { cachedCases.value = UiState.Data(it) }
        }
    }
}
