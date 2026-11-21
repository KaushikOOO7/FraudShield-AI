package com.fraudshield.app.feature.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fraudshield.app.core.model.Investigation
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.FraudRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class HistoryViewModel @Inject constructor(private val repository: FraudRepository) : ViewModel() {
    private val cachedCases = MutableStateFlow<UiState<List<Investigation>>>(UiState.Loading)
    private val refreshState = MutableStateFlow<UiState<Unit>>(UiState.Data(Unit))
    private var observation: Job? = null
    private var refresh: Job? = null
    private val mutableCursor = MutableStateFlow<String?>(null)
    val nextCursor = mutableCursor.asStateFlow()
    private val mutablePageError = MutableStateFlow<String?>(null)
    val pageError = mutablePageError.asStateFlow()
    private val mutableLoadingMore = MutableStateFlow(false)
    val loadingMore = mutableLoadingMore.asStateFlow()
    private var pagination: Job? = null
    private val seenCursors = mutableSetOf<String>()
    private val mutableDelete=MutableStateFlow<String?>(null);val pendingDelete=mutableDelete.asStateFlow()
    val canFeedback get()=repository.canFeedback
    fun requestDelete(id:String){mutableDelete.value=id}
    fun cancelDelete(){mutableDelete.value=null}
    fun delete(){val id=pendingDelete.value?:return;viewModelScope.launch{runCatching{repository.deleteCase(id)}.onFailure{mutablePageError.value=it.toUiError().message};mutableDelete.value=null}}
    fun markSafe(id:String){viewModelScope.launch{runCatching{repository.feedback(id)}.onFailure{mutablePageError.value=it.toUiError().message}}}
    private val mutableQuery = MutableStateFlow("")
    val query = mutableQuery.asStateFlow()
    private val mutableFilter = MutableStateFlow("all")
    val filter = mutableFilter.asStateFlow()

    val state = combine(cachedCases, query, filter, refreshState) { cached, query, filter, refreshing ->
        when (refreshing) {
            UiState.Loading -> UiState.Loading
            is UiState.Error -> refreshing
            else -> when (cached) {
                is UiState.Data -> {
                    val cases = cached.value.filter { case ->
                        (filter == "all" || case.type?.wireValue == filter) &&
                            (query.isBlank() || case.caseId.contains(query, true) || case.reasons.any { it.contains(query, true) })
                    }
                    if (cases.isEmpty()) UiState.Empty else UiState.Data(cases)
                }
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

    fun search(value: String) { mutableQuery.value = value }
    fun filter(value: String) {
        mutableFilter.value = value
        pagination?.cancel(); mutableLoadingMore.value = false; mutableCursor.value = null
        if (repository.canSync) retry()
    }
    fun retry() {
        refresh?.cancel()
        pagination?.cancel()
        mutableLoadingMore.value = false
        seenCursors.clear()
        mutableCursor.value = null
        mutablePageError.value = null
        refresh = viewModelScope.launch {
            refreshState.value = UiState.Loading
            if (repository.canSync) {
                runCatching { repository.refreshHistory(filter = filter.value) }
                    .onFailure { refreshState.value = it.toUiError() }
                    .onSuccess { mutableCursor.value = it.nextCursor; refreshState.value = UiState.Data(Unit) }
            } else {
                observeCache()
                refreshState.value = UiState.Data(Unit)
            }
        }
    }

    fun showSaved() { refresh?.cancel(); refreshState.value = UiState.Data(Unit); observeCache() }

    fun loadMore() {
        val cursor = nextCursor.value ?: return
        if (mutableLoadingMore.value || !repository.canSync) return
        pagination = viewModelScope.launch {
            mutableLoadingMore.value = true
            mutablePageError.value = null
            try {
                val page = repository.refreshHistory(cursor, filter.value)
                seenCursors.add(cursor)
                mutableCursor.value = page.nextCursor?.takeUnless { it in seenCursors }
                if (page.nextCursor != null && page.nextCursor in seenCursors) mutablePageError.value = "The service repeated a history cursor. Refresh to try again."
            } catch (error: kotlinx.coroutines.CancellationException) { throw error }
            catch (error: Throwable) { mutablePageError.value = error.toUiError().message }
            finally { mutableLoadingMore.value = false }
        }
    }

    private fun observeCache() {
        observation?.cancel()
        observation = viewModelScope.launch {
            repository.observeHistory().catch { cachedCases.value = it.toUiError() }
                .collect { cachedCases.value = UiState.Data(it) }
        }
    }
}
