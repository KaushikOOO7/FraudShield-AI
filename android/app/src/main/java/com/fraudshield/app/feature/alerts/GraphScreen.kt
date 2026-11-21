package com.fraudshield.app.feature.alerts

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.*
import com.fraudshield.app.data.repository.ClientDataRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.cos
import kotlin.math.sin

@HiltViewModel class GraphViewModel @Inject constructor(private val data: ClientDataRepository,
    savedState: SavedStateHandle, @ApplicationContext private val context: Context,
    private val dispatchers: DispatcherProvider) : ViewModel() {
    private val id = savedState.get<String>("caseId")
    private val mutable = MutableStateFlow<UiState<InvestigationGraph>>(UiState.Loading)
    val state = mutable.asStateFlow()
    private val exportMutable = MutableStateFlow<UiState<File>>(UiState.Empty)
    val export = exportMutable.asStateFlow()
    init { retry() }
    fun retry() { viewModelScope.launch { mutable.value = UiState.Loading
        runCatching { id?.let { data.graph(it) } }.onSuccess { mutable.value = if (it == null || it.nodes.isEmpty()) UiState.Empty else UiState.Data(it) }
            .onFailure { mutable.value = it.toUiError() }
    } }
    fun export() { val graph = (state.value as? UiState.Data<InvestigationGraph>)?.value ?: return
        viewModelScope.launch { exportMutable.value = UiState.Loading
            runCatching { withContext(dispatchers.io) {
                val bitmap = Bitmap.createBitmap(1200, 1200, Bitmap.Config.ARGB_8888)
                val canvas = android.graphics.Canvas(bitmap); canvas.drawColor(android.graphics.Color.rgb(11,18,32))
                drawGraph(canvas, graph, 1200f, 1200f)
                if(data.isDemo)canvas.drawText("DEMO",40f,60f,android.graphics.Paint().apply{color=android.graphics.Color.WHITE;textSize=36f})
                val directory = File(context.cacheDir, "shared").apply { mkdirs() }
                File(directory, "graph-${System.currentTimeMillis()}.png").also { file ->
                    file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }; bitmap.recycle()
                }
            } }.onSuccess { exportMutable.value = UiState.Data(it) }.onFailure { exportMutable.value = it.toUiError() }
        }
    }
    fun consumeExport() { exportMutable.value = UiState.Empty }
}

private fun positions(graph: InvestigationGraph, width: Float, height: Float): Map<String, Offset> = graph.nodes.take(60).mapIndexed { i, node ->
    val angle = 2 * Math.PI * i / graph.nodes.take(60).size.coerceAtLeast(1)
    node.id to Offset(width / 2 + cos(angle).toFloat() * width * .32f, height / 2 + sin(angle).toFloat() * height * .32f)
}.toMap()
private fun drawGraph(canvas: android.graphics.Canvas, graph: InvestigationGraph, width: Float, height: Float) {
    val points = positions(graph, width, height)
    val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply { color = android.graphics.Color.rgb(56,189,248); strokeWidth = 3f }
    graph.edges.forEach { edge -> val a = points[edge.from]; val b = points[edge.to]
        if (a != null && b != null) canvas.drawLine(a.x, a.y, b.x, b.y, paint) }
    graph.nodes.take(60).forEach { node -> points[node.id]?.let { p ->
        paint.color = android.graphics.Color.rgb(52,211,153); canvas.drawCircle(p.x,p.y,16f,paint)
        paint.color = android.graphics.Color.rgb(229,234,243); paint.textSize = (width / 35).coerceAtLeast(18f)
        canvas.drawText(node.label.take(28), p.x - 32f, p.y + 40f, paint)
    } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun GraphScreen() {
    val model: GraphViewModel = hiltViewModel()
    val state by model.state.collectAsStateWithLifecycle(); val export by model.export.collectAsStateWithLifecycle()
    var selected by remember { mutableStateOf<GraphNode?>(null) }; var shareError by remember { mutableStateOf(false) }
    val context = LocalContext.current
    LaunchedEffect(export) { (export as? UiState.Data<File>)?.value?.let { file ->
        try { shareFile(context,file,"image/png") } catch (error: android.content.ActivityNotFoundException) { android.util.Log.w("FraudShield", "Graph sharing unavailable"); shareError = true }
        finally { model.consumeExport() }
    } }
    ScreenList {
        item { Notice(stringResource(R.string.graph_nodes)) }
        item { StateContent(state,stringResource(R.string.graph_empty),stringResource(R.string.graph_description),model::retry) { graph ->
            Column {
                Canvas(Modifier.fillMaxWidth().height(360.dp).pointerInput(graph) { detectTapGestures { tap ->
                    selected = graph.nodes.firstOrNull { node -> positions(graph,size.width.toFloat(),size.height.toFloat())[node.id]?.let { (it-tap).getDistance() < 40f } == true }
                } }) { drawGraph(drawContext.canvas.nativeCanvas,graph,size.width,size.height) }
                graph.nodes.forEach { node -> SecondaryButton(node.label + " · " + node.kind, { selected = node }) }
                PrimaryButton(stringResource(R.string.share_graph),model::export)
            }
        } }
        if (export is UiState.Loading) item { Text(stringResource(R.string.loading)) }
        if (export is UiState.Error || shareError) item { Notice(stringResource(R.string.error_generic),true) }
    }
    selected?.let { node -> ModalBottomSheet({ selected = null }) {
        Column(Modifier.padding(20.dp)) { Text(node.label,style=MaterialTheme.typography.titleLarge); Text(node.kind)
            Text((state as? UiState.Data<InvestigationGraph>)?.value?.edges.orEmpty().filter { it.from==node.id||it.to==node.id }.joinToString("\n") { "${it.from} ${it.rel} ${it.to}" })
            SecondaryButton(stringResource(R.string.close),{ selected=null }) }
    } }
}
