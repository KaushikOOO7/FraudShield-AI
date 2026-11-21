package com.fraudshield.app.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.ProtectionPermission
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.PermissionHealthRepository
import com.fraudshield.app.data.repository.PreferencesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class PermissionsViewModel @Inject constructor(private val preferences: PreferencesRepository,
    private val permissions: PermissionHealthRepository) : ViewModel() {
    val health = permissions.health
    private val mutableError = MutableStateFlow<String?>(null)
    val error = mutableError.asStateFlow()
    init { refresh() }
    fun refresh() { viewModelScope.launch {
        runCatching { permissions.refresh() }.onSuccess { mutableError.value = null }
            .onFailure { mutableError.value = it.toUiError().message }
    } }
    fun consent(enabled: Boolean) { preferences.monitoringConsent(enabled); refresh() }
    fun permission(permission: ProtectionPermission, enabled: Boolean) { preferences.permission(permission, enabled); refresh() }
    fun allow(packageName: String, enabled: Boolean) { preferences.allowPackage(packageName, enabled); refresh() }
    fun finish() { preferences.finishOnboarding() }
    fun actionFailed() { mutableError.value = "This device could not open the permission screen. Use app settings or skip for now." }
}
