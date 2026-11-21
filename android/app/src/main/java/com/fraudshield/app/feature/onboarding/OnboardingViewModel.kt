package com.fraudshield.app.feature.onboarding

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel @Inject constructor(private val savedState: SavedStateHandle) : ViewModel() {
    val page = savedState.getStateFlow("page", 0)
    fun next() { savedState["page"] = (page.value + 1).coerceAtMost(2) }
}
