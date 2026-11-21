package com.fraudshield.app.feature.alerts

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.AgentStatus
import com.fraudshield.app.core.model.Agent
import com.fraudshield.app.core.model.CaseSource
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription

enum class AlertsDestination { Detail, Graph, Report }

/** One entry for alert detail, graph and report destinations. */
@Composable
fun AlertsRoute(destination: AlertsDestination, onGraph: (String) -> Unit, onFamily: () -> Unit, onEmergency: () -> Unit) {
    when (destination) {
        AlertsDestination.Detail -> AlertDetail(onGraph, onFamily, onEmergency)
        AlertsDestination.Graph -> GraphScreen()
        AlertsDestination.Report -> ReportScreen()
    }
}

@Composable
private fun AlertDetail(onGraph: (String) -> Unit, onFamily: () -> Unit, onEmergency: () -> Unit) {
    val model: AlertViewModel = hiltViewModel()
    val state by model.state.collectAsStateWithLifecycle()
    val clipboard = LocalClipboardManager.current
    ScreenList {
        item {
            StateContent(state, stringResource(R.string.case_empty), stringResource(R.string.case_empty_body), { model.retry() }) { case ->
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    ShieldCard {
                        VerdictBadge(case.verdict)
                        Text(case.caseId, style = MaterialTheme.typography.titleLarge)
                        RiskGauge(case)
                        Text(stringResource(R.string.verdict_limit), color = ShieldColors.TextMid)
                        case.localMetadata?.let { metadata ->
                            Notice(stringResource(when (metadata.source) {
                                CaseSource.SERVICE -> R.string.result_from_service
                                CaseSource.SAVED -> R.string.result_from_cache
                                CaseSource.DEMO -> R.string.result_from_demo
                            }))
                            val saved = DateTimeFormatter.ofPattern("dd MMM yyyy, HH:mm").withZone(ZoneId.systemDefault())
                                .format(Instant.ofEpochMilli(metadata.savedAt))
                            Text(stringResource(R.string.saved_at, saved), color = ShieldColors.TextMid)
                        }
                        SecondaryButton(stringResource(R.string.refresh_case), { model.retry(true) }, model.canRefresh)
                    }
                    ShieldCard {
                        SectionLabel(stringResource(R.string.why_flagged))
                        if (case.reasons.isEmpty()) Text(stringResource(R.string.no_reasons), color = ShieldColors.TextMid)
                        case.reasons.forEachIndexed { index, reason -> Text("${index + 1}. $reason") }
                    }
                    ShieldCard {
                        SectionLabel(stringResource(R.string.agent_findings))
                        if (case.agentFindings.isEmpty()) Text(stringResource(R.string.no_findings), color = ShieldColors.TextMid)
                        case.agentFindings.forEach { finding ->
                            var expanded by remember(case.caseId, finding.agent) { mutableStateOf(false) }
                            val status = when (finding.status) {
                                AgentStatus.OK -> R.string.agent_ok
                                AgentStatus.LOW -> R.string.agent_low
                                AgentStatus.SUSPICIOUS -> R.string.agent_suspicious
                                AgentStatus.HIGH -> R.string.agent_high
                            }
                            val expansion = stringResource(if (expanded) R.string.expanded else R.string.collapsed)
                            val agentLabel = stringResource(when (finding.agent) {
                                Agent.Message -> R.string.agent_message_name
                                Agent.Call -> R.string.agent_call_name
                                Agent.Link -> R.string.agent_link_name
                                Agent.Behavior -> R.string.agent_behavior_name
                            })
                            TextButton({ expanded = !expanded }, Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { stateDescription = expansion }) {
                                Text("● $agentLabel · ${stringResource(status)}", Modifier.weight(1f))
                                Text(if (expanded) "−" else "+")
                            }
                            Text(finding.detail, color = ShieldColors.TextMid)
                            if (expanded) {
                                if (finding.signals.isEmpty()) Text(stringResource(R.string.no_signals), color = ShieldColors.TextMid)
                                finding.signals.forEach { Text("• $it") }
                            }
                            HorizontalDivider(color = ShieldColors.Border)
                        }
                    }
                    ShieldCard {
                        SectionLabel(stringResource(R.string.extracted_entities))
                        val entities = case.entities.urls + case.entities.phones
                        if (entities.isEmpty()) Text(stringResource(R.string.no_entities), color = ShieldColors.TextMid)
                        entities.forEach { entity ->
                            SecondaryButton(stringResource(R.string.copy_entity, entity), { clipboard.setText(AnnotatedString(entity)) })
                        }
                        if (case.entities.otpRequest) Text(stringResource(R.string.otp_reminder), color = ShieldColors.Caution)
                    }
                    ShieldCard {
                        SectionLabel(stringResource(R.string.recommended_actions))
                        ActionButtons(case.actions,stringResource(case.verdict.labelResource()),case.caseId)
                        PrimaryButton(stringResource(R.string.emergency), onEmergency)
                        SecondaryButton(stringResource(R.string.view_graph), { onGraph(case.caseId) })
                        SecondaryButton(stringResource(R.string.warn_family), onFamily)
                    }
                    ShieldCard {
                        SectionLabel(stringResource(R.string.correction_title))
                        Text(stringResource(R.string.correction_explanation), color = ShieldColors.TextMid)
                        if (!model.canFeedback) Notice(stringResource(R.string.feedback_pending))
                        SecondaryButton(stringResource(R.string.mark_as_safe), model::markSafe, model.canFeedback)
                        val feedback by model.feedback.collectAsStateWithLifecycle()
                        StateContent(feedback, stringResource(R.string.correction_empty), stringResource(R.string.correction_explanation), model::markSafe) {
                            Text(stringResource(if (case.localMetadata?.source == CaseSource.DEMO) R.string.demo_feedback else R.string.feedback_received, it.status))
                        }
                    }
                }
            }
        }
    }
}
