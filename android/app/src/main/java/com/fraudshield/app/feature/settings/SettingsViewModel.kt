package com.fraudshield.app.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.DataCounts
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.ClientDataRepository
import com.fraudshield.app.data.repository.PermissionHealthRepository
import com.fraudshield.app.data.repository.PreferencesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val preferences: PreferencesRepository,
    private val permissions: PermissionHealthRepository,
    private val data: ClientDataRepository
) : ViewModel() {
    val health = permissions.health
    val counts = data.counts()
        .map { val value: UiState<DataCounts> = UiState.Data(it); value }
        .catch { emit(it.toUiError()) }
        .stateIn(viewModelScope, SharingStarted.Eagerly, UiState.Loading)

    private val mutableOperation = MutableStateFlow<UiState<String>>(UiState.Empty)
    val operation = mutableOperation.asStateFlow()

    private val mutableExport = MutableStateFlow<File?>(null)
    val export = mutableExport.asStateFlow()

    val canDeleteRemote get() = data.deletionReady

    fun delete(remote: Boolean) {
        viewModelScope.launch {
            mutableOperation.value = UiState.Loading
            runCatching { data.deleteAll(remote) }
                .onSuccess {
                    mutableOperation.value = UiState.Data(if (remote) "REMOTE_CONFIRMED" else "LOCAL_ONLY")
                }
                .onFailure { mutableOperation.value = it.toUiError() }
        }
    }

    fun export() {
        viewModelScope.launch {
            mutableOperation.value = UiState.Loading
            runCatching { data.export() }
                .onSuccess {
                    mutableExport.value = it
                    mutableOperation.value = UiState.Empty
                }
                .onFailure { mutableOperation.value = it.toUiError() }
        }
    }

    fun consumeExport() {
        mutableExport.value = null
    }

    fun monitoring(enabled: Boolean) {
        preferences.monitoring(enabled)
        refresh()
    }

    fun withdraw() {
        preferences.monitoringConsent(false)
        refresh()
    }

    private fun refresh() {
        viewModelScope.launch {
            runCatching { permissions.refresh() }
                .onFailure { it.toUiError() }
        }
    }
}
