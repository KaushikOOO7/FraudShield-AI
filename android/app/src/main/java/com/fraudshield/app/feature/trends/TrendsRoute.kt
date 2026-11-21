package com.fraudshield.app.feature.trends

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.res.stringResource
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

@Composable
fun TrendsRoute() {
    val model: TrendsViewModel = hiltViewModel(); val state by model.state.collectAsStateWithLifecycle(); val range by model.range.collectAsStateWithLifecycle()
    ScreenList {
        item { Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) { listOf("7d","30d").forEach { value -> FilterChip(range==value,{model.range(value)},{Text(value)}) } } }
        item { StateContent(state,stringResource(R.string.no_trends),stringResource(R.string.trends_description),model::retry) { trends ->
            Column(verticalArrangement=Arrangement.spacedBy(16.dp)) {
                ShieldCard { Text(stringResource(R.string.total_scans,trends.totalScanned)); Text(stringResource(R.string.service_blocked,trends.threatsBlocked)) }
                ShieldCard { SectionLabel(stringResource(R.string.weekly_volume))
                    Canvas(Modifier.fillMaxWidth().height(180.dp)) { val max=trends.weekly.maxOfOrNull { it.count }?.coerceAtLeast(1) ?: 1
                        val bar=size.width/trends.weekly.size.coerceAtLeast(1)
                        trends.weekly.forEachIndexed { i,v -> val h=size.height*v.count/max
                            drawRect(ShieldColors.Secondary,Offset(i*bar+4,size.height-h),Size((bar-8).coerceAtLeast(1f),h)) }
                    }
                    trends.weekly.forEach { Text("${it.day}: ${it.count}") }
                }
                ShieldCard { SectionLabel(stringResource(R.string.categories)); val max=trends.categories.maxOfOrNull { it.count }?.coerceAtLeast(1) ?: 1
                    trends.categories.forEach { Text("${it.label}: ${it.count}"); LinearProgressIndicator(progress=it.count.toFloat()/max,modifier=Modifier.fillMaxWidth()) } }
                trends.topVectors.take(3).forEach { vector -> ShieldCard { Text(vector.label); Text("${vector.pct}%") } }
            }
        } }
    }
}
