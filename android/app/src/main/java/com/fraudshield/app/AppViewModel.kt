package com.fraudshield.app

import androidx.lifecycle.ViewModel
import com.fraudshield.app.data.repository.PreferencesRepository
import com.fraudshield.app.data.repository.PermissionHealthRepository
import com.fraudshield.app.core.network.toUiError
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.launch
import com.fraudshield.app.data.monitoring.PendingSignalStore
import com.fraudshield.app.data.repository.CaseContextStore

@HiltViewModel
class AppViewModel @Inject constructor(private val preferences: PreferencesRepository,
    private val permissions: PermissionHealthRepository, private val pendingSignals: PendingSignalStore,
    private val selection:CaseContextStore) : ViewModel() {
    val locale = preferences.locale
    val protection = preferences.protection
    val erasureEpoch=preferences.erasureEpoch
    val health = permissions.health
    init { viewModelScope.launch { runCatching { pendingSignals.removeExpired() }.onFailure { it.toUiError() } } }
    fun setLocale(value: String) { preferences.setLocale(value) }
    fun selectCase(id:String?){selection.select(id)}
    fun refreshHealth() { viewModelScope.launch { runCatching { permissions.refresh() }.onFailure { it.toUiError() } } }
}
