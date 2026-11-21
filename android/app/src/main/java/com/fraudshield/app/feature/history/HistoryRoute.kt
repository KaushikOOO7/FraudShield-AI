package com.fraudshield.app.feature.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.UiState
import androidx.compose.runtime.remember

@OptIn(ExperimentalLayoutApi::class,ExperimentalMaterial3Api::class)
@Composable
fun HistoryRoute(onCase: (String) -> Unit,onReport:(String)->Unit={}) {
    val model: HistoryViewModel = hiltViewModel()
    val state by model.state.collectAsStateWithLifecycle()
    val query by model.query.collectAsStateWithLifecycle()
    val filter by model.filter.collectAsStateWithLifecycle()
    val cursor by model.nextCursor.collectAsStateWithLifecycle()
    val loadingMore by model.loadingMore.collectAsStateWithLifecycle()
    val pageError by model.pageError.collectAsStateWithLifecycle()
    val pendingDelete by model.pendingDelete.collectAsStateWithLifecycle()
    val filters = listOf("all" to R.string.filter_all, "sms" to R.string.filter_sms,
        "call" to R.string.filter_calls, "url" to R.string.filter_links, "qr" to R.string.filter_qr)
    ScreenList {
        item {
            OutlinedTextField(query, model::search, Modifier.fillMaxWidth(), label = { Text(stringResource(R.string.search_history)) }, singleLine = true)
        }
        item { SecondaryButton(stringResource(R.string.refresh_history), model::retry) }
        if (state is UiState.Error) item { SecondaryButton(stringResource(R.string.use_saved_checks), model::showSaved) }
        item {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                filters.forEach { (value, label) ->
                    FilterChip(filter == value, { model.filter(value) }, { Text(stringResource(label)) })
                }
            }
        }
        when (val current = state) {
            is UiState.Data -> {
                val groups = current.value.groupBy { it.createdAt?.substringBefore('T') }
                groups.forEach { (date, cases) ->
                    item(key = "day-$date") { SectionLabel(date ?: stringResource(R.string.date_unavailable)) }
                    items(cases, key = { it.caseId }) { case ->
                        val swipe=rememberSwipeToDismissBoxState(confirmValueChange={value->when(value){SwipeToDismissBoxValue.StartToEnd->onReport(case.caseId);SwipeToDismissBoxValue.EndToStart->model.requestDelete(case.caseId);SwipeToDismissBoxValue.Settled->Unit};false})
                        SwipeToDismissBox(state=swipe,backgroundContent={Text(stringResource(R.string.swipe_history_hint))}){
                            Column{CaseSummary(case){onCase(case.caseId)}
                                SecondaryButton(stringResource(R.string.submit_report),{onReport(case.caseId)})
                                SecondaryButton(stringResource(R.string.delete_local),{model.requestDelete(case.caseId)})
                                SecondaryButton(stringResource(R.string.mark_as_safe),{model.markSafe(case.caseId)},model.canFeedback)
                            }
                        }
                    }
                }
            }
            else -> item { StateContent(state, stringResource(R.string.history_empty_title), stringResource(R.string.history_empty_body), model::retry) {} }
        }
        pageError?.let { error -> item { Notice(error, caution = true) } }
        if (cursor != null) item {
            SecondaryButton(stringResource(if (loadingMore) R.string.loading else R.string.load_more), model::loadMore, !loadingMore)
        }
    }
    pendingDelete?.let{AlertDialog(onDismissRequest=model::cancelDelete,title={Text(stringResource(R.string.delete_local))},text={Text(stringResource(R.string.local_case_delete))},confirmButton={TextButton(model::delete){Text(stringResource(R.string.delete_local))}},dismissButton={TextButton(model::cancelDelete){Text(stringResource(R.string.cancel))}})}
}
