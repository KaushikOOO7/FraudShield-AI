package com.fraudshield.app.feature.home

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.ProtectionStatus
import com.fraudshield.app.core.model.UiState

@Composable
fun HomeRoute(onNavigate: (String) -> Unit, onCase: (String) -> Unit) {
    val model: HomeViewModel = hiltViewModel()
    val alerts by model.alerts.collectAsStateWithLifecycle()
    val health by model.health.collectAsStateWithLifecycle()
    val counts by model.counts.collectAsStateWithLifecycle()
    val status = stringResource(when (health.status) {
        ProtectionStatus.PROTECTED -> R.string.protected_status
        ProtectionStatus.ATTENTION -> R.string.attention_needed
        ProtectionStatus.PAUSED -> R.string.monitoring_paused
    })
    val statusColor = when (health.status) {
        ProtectionStatus.PROTECTED -> ShieldColors.Primary
        ProtectionStatus.ATTENTION -> ShieldColors.Caution
        ProtectionStatus.PAUSED -> ShieldColors.Secondary
    }
    ScreenList {
        item {
            Text(stringResource(R.string.home_greeting), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.home_subtitle), color = ShieldColors.TextMid)
        }
        item {
            ShieldCard {
                Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(Modifier.size(144.dp).semantics { contentDescription = status }, contentAlignment = Alignment.Center) {
                        Canvas(Modifier.fillMaxSize().padding(8.dp)) {
                            drawCircle(statusColor.copy(alpha = 0.6f), style = Stroke(8.dp.toPx()))
                            drawCircle(statusColor.copy(alpha = 0.06f))
                        }
                        Icon(Icons.Outlined.Shield, stringResource(R.string.shield), tint = statusColor, modifier = Modifier.size(52.dp))
                    }
                    Text(status, style = MaterialTheme.typography.titleLarge)
                    Text(stringResource(if (health.status == ProtectionStatus.PROTECTED) R.string.enabled_scope else R.string.manual_mode_body), color = ShieldColors.TextMid)
                }
                PrimaryButton(stringResource(R.string.enable_protection), { onNavigate("permissions") })
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.protection_summary))
                StateContent(counts, stringResource(R.string.history_empty_title), stringResource(R.string.history_empty_body), model::showSaved) { count ->
                    Text(stringResource(R.string.saved_check_count, count.first))
                    Text(stringResource(R.string.attention_check_count, count.second))
                    Text(stringResource(R.string.active_source_count, health.activeSources))
                }
                Text(stringResource(R.string.no_auto_blocking), style = MaterialTheme.typography.bodyMedium, color = ShieldColors.TextMid)
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.quick_checks))
                PrimaryButton(stringResource(R.string.paste_check), { onNavigate("scan?tab=text") })
                SecondaryButton(stringResource(R.string.scan_qr), { onNavigate("scan?tab=qr") })
                SecondaryButton(stringResource(R.string.check_number), { onNavigate("scan?tab=call") })
                SecondaryButton(stringResource(R.string.submit_report), { onNavigate("report") })
            }
        }
        item { SectionLabel(stringResource(R.string.recent_alerts)) }
        if (alerts is UiState.Error) item { SecondaryButton(stringResource(R.string.use_saved_checks), model::showSaved) }
        item {
            StateContent(alerts, stringResource(R.string.history_empty_title), stringResource(R.string.history_empty_body), model::retry) { cases ->
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    cases.forEach { case -> CaseSummary(case) { onCase(case.caseId) } }
                }
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.explore))
                SecondaryButton(stringResource(R.string.assistant), { onNavigate("assistant") })
                SecondaryButton(stringResource(R.string.trends), { onNavigate("trends") })
                SecondaryButton(stringResource(R.string.family), { onNavigate("family") })
                SecondaryButton(stringResource(R.string.emergency), { onNavigate("emergency") })
            }
        }
    }
}
