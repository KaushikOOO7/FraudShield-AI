package com.fraudshield.app

import app.cash.turbine.test
import com.fraudshield.app.core.model.*
import com.fraudshield.app.data.repository.FraudRepository
import com.fraudshield.app.feature.history.HistoryViewModel
import java.io.IOException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HistoryViewModelTest {
    @get:Rule val main = MainDispatcherRule()

    @Test
    fun deniedMonitoringCanShowAnEmptyLocalHistoryWithoutNetwork() = runTest {
        val repository = HistoryTestRepository(emptyList(), demo = false)
        val model = HistoryViewModel(repository)
        model.state.test {
            assertEquals(UiState.Loading, awaitItem())
            advanceUntilIdle()
            assertEquals(UiState.Empty, awaitItem())
            assertEquals(0, repository.refreshes)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun filterAndSearchUseRepositoryCasesWithoutChangingVerdicts() = runTest {
        val repository = HistoryTestRepository(cases(), demo = false)
        val model = HistoryViewModel(repository)
        advanceUntilIdle()
        model.filter("call")
        advanceUntilIdle()
        model.state.test {
            val data = awaitItem() as UiState.Data<List<Investigation>>
            assertEquals(listOf("DEMO-CALL"), data.value.map { it.caseId })
            assertEquals(Verdict.CAUTION, data.value.single().verdict)
            model.search("does not exist")
            advanceUntilIdle()
            assertEquals(UiState.Empty, awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun fixtureReadFailureIsVisibleAndCanBeRetried() = runTest {
        val repository = HistoryTestRepository(emptyList(), demo = true).apply { failRefresh = true }
        val model = HistoryViewModel(repository)
        advanceUntilIdle()
        assertTrue(model.state.value is UiState.Error)
        repository.failRefresh = false
        model.retry()
        advanceUntilIdle()
        assertTrue(model.state.value is UiState.Data)
        assertEquals(2, repository.refreshes)
    }

    private fun cases(): List<Investigation> = requireNotNull(javaClass.classLoader?.getResourceAsStream("demo/cases.json"))
        .bufferedReader().use { Json.decodeFromString(it.readText()) }
}

private class HistoryTestRepository(initial: List<Investigation>, private val demo: Boolean) : FraudRepository {
    override val isDemo: Boolean = demo
    private val history = MutableStateFlow(initial)
    var refreshes = 0
    var failRefresh = false
    override fun observeHistory() = history
    override suspend fun refreshHistory(cursor: String?, filter: String): HistoryPage {
        refreshes += 1
        if (failRefresh) throw IOException("Deliberate fixture read failure")
        val stream = requireNotNull(javaClass.classLoader?.getResourceAsStream("demo/cases.json"))
        val items = stream.bufferedReader().use { Json.decodeFromString<List<Investigation>>(it.readText()) }
        history.value = items
        return HistoryPage(items)
    }
    override suspend fun getCase(id: String) = history.value.first { it.caseId == id }
    override suspend fun analyze(request: AnalyzeRequest): Investigation = error("Not used by history tests")
    override suspend fun graph(id: String): InvestigationGraph = error("Not used by history tests")
    override suspend fun trends(range: String): Trends = error("Not used by history tests")
    override suspend fun assistant(request: AssistantRequest): AssistantAnswer = error("Not used by history tests")
    override suspend fun report(request: ReportRequest): ReportReceipt = error("Not used by history tests")
    override suspend fun familyAlert(request: FamilyAlertRequest): FamilyAlertReceipt = error("Not used by history tests")
    override suspend fun health(): Health = error("Not used by history tests")
}
