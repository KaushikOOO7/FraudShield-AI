package com.fraudshield.app.core.designsystem

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.fraudshield.app.R
import com.fraudshield.app.core.model.Investigation
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.model.Verdict

@Composable
fun ShieldCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, ShieldColors.Border),
        shadowElevation = 2.dp,
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

@Composable
fun ScreenList(content: LazyListScope.() -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        content = content,
    )
}

@Composable
fun SectionLabel(text: String) {
    Text(text, style = MaterialTheme.typography.labelMedium, color = ShieldColors.TextMid,
        modifier = Modifier.semantics { heading() })
}

@Composable
fun PrimaryButton(label: String, onClick: () -> Unit, enabled: Boolean = true) {
    Button(onClick, Modifier.fillMaxWidth().heightIn(min = 52.dp), enabled = enabled, shape = RoundedCornerShape(16.dp)) {
        Text(label, Modifier.padding(vertical = 4.dp))
    }
}

@Composable
fun SecondaryButton(label: String, onClick: () -> Unit, enabled: Boolean = true) {
    OutlinedButton(onClick, Modifier.fillMaxWidth().heightIn(min = 48.dp), enabled = enabled, shape = RoundedCornerShape(16.dp)) {
        Text(label, Modifier.padding(vertical = 4.dp))
    }
}

@Composable
fun Notice(text: String, caution: Boolean = false) {
    val color = if (caution) ShieldColors.Caution else ShieldColors.Secondary
    Surface(color = color.copy(alpha = 0.08f), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, color.copy(alpha = 0.35f))) {
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(Icons.Outlined.Info, stringResource(R.string.information), tint = color, modifier = Modifier.size(24.dp))
            Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        }
    }
}

/** All typed backend verdicts pass through this badge, including list and detail surfaces. */
@Composable
fun VerdictBadge(verdict: Verdict, modifier: Modifier = Modifier) {
    val color = verdict.color()
    val label = stringResource(verdict.labelResource())
    val icon = when (verdict) {
        Verdict.VERIFIED, Verdict.SAFE -> Icons.Outlined.CheckCircle
        Verdict.CAUTION -> Icons.Outlined.Info
        Verdict.HIGH_RISK, Verdict.CONFIRMED_FRAUD -> Icons.Outlined.WarningAmber
    }
    val confirmed = verdict == Verdict.CONFIRMED_FRAUD
    Surface(
        modifier = modifier.semantics(mergeDescendants = true) {},
        color = if (confirmed) ShieldColors.DangerSolid else color.copy(alpha = 0.12f),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.5f)),
    ) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(icon, label, tint = if (confirmed) Color.White else color, modifier = Modifier.size(20.dp))
            Text(label, style = MaterialTheme.typography.labelLarge, color = if (confirmed) Color.White else color)
        }
    }
}

fun Verdict.color(): Color = when (this) {
    Verdict.VERIFIED, Verdict.SAFE -> ShieldColors.Safe
    Verdict.CAUTION -> ShieldColors.Caution
    Verdict.HIGH_RISK, Verdict.CONFIRMED_FRAUD -> ShieldColors.Danger
}

fun Verdict.labelResource(): Int = when (this) {
    Verdict.VERIFIED -> R.string.verdict_verified
    Verdict.SAFE -> R.string.verdict_safe
    Verdict.CAUTION -> R.string.verdict_caution
    Verdict.HIGH_RISK -> R.string.verdict_high_risk
    Verdict.CONFIRMED_FRAUD -> R.string.verdict_confirmed_fraud
}

@Composable
fun RiskGauge(case: Investigation) {
    val fraction by animateFloatAsState(case.riskScore / 100f, label = "risk")
    val description = stringResource(R.string.risk_score_value, case.riskScore)
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth().semantics(mergeDescendants = true) {
        contentDescription = description
    }) {
        Box(Modifier.size(176.dp), contentAlignment = Alignment.Center) {
            Canvas(Modifier.fillMaxSize().padding(12.dp)) {
                val stroke = 10.dp.toPx()
                val inset = stroke / 2
                val bounds = Size(size.width - stroke, size.height - stroke)
                drawArc(ShieldColors.Border, 135f, 270f, false, Offset(inset, inset), bounds, style = Stroke(stroke, cap = StrokeCap.Round))
                drawArc(case.verdict.color(), 135f, 270f * fraction, false, Offset(inset, inset), bounds, style = Stroke(stroke, cap = StrokeCap.Round))
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(case.riskScore.toString(), style = MaterialTheme.typography.headlineLarge)
                Text(stringResource(R.string.out_of_100), style = MaterialTheme.typography.bodyMedium, color = ShieldColors.TextMid)
            }
        }
        Text(stringResource(R.string.risk_score), style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
fun <T> StateContent(
    state: UiState<T>,
    emptyTitle: String,
    emptyBody: String,
    onRetry: () -> Unit,
    content: @Composable (T) -> Unit,
) {
    when (state) {
        UiState.Loading -> Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
                CircularProgressIndicator(Modifier.size(32.dp), strokeWidth = 3.dp)
                Text(stringResource(R.string.loading), color = ShieldColors.TextMid)
            }
        }
        UiState.Empty -> ShieldCard {
            Icon(Icons.Outlined.Shield, stringResource(R.string.shield), tint = ShieldColors.Secondary)
            Text(emptyTitle, style = MaterialTheme.typography.titleLarge)
            Text(emptyBody, color = ShieldColors.TextMid)
        }
        is UiState.Error -> ShieldCard {
            Text(stringResource(R.string.could_not_load), style = MaterialTheme.typography.titleLarge)
            Text(localizedError(state), color = ShieldColors.TextMid)
            SecondaryButton(stringResource(R.string.retry), onRetry)
        }
        is UiState.Data -> content(state.value)
    }
}

@Composable
private fun localizedError(error: UiState.Error): String {
    val resource = when (error.code) {
        "OFFLINE" -> R.string.error_offline
        "CONSENT_REQUIRED" -> R.string.error_consent
        "INPUT", "INVALID_PAYLOAD", "VALIDATION_ERROR" -> R.string.error_input
        "BACKEND_NOT_CONFIGURED", "FEATURE_UNAVAILABLE" -> R.string.backend_pending
        "RATE_LIMITED" -> R.string.error_rate_limit
        "CASE_NOT_FOUND", "NOT_FOUND" -> R.string.case_empty_body
        "TOKEN_EXPIRED", "UNAUTHORIZED" -> R.string.error_session
        "INVALID_RESPONSE" -> R.string.error_response
        "SERVICE_UNAVAILABLE", "MODEL_UNAVAILABLE" -> R.string.error_service
        null -> return error.message
        else -> R.string.error_generic
    }
    return stringResource(resource)
}

@Composable
fun CaseSummary(case: Investigation, onOpen: () -> Unit) {
    ShieldCard {
        VerdictBadge(case.verdict)
        Text(case.caseId, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text(case.reasons.firstOrNull() ?: stringResource(R.string.no_reasons), color = ShieldColors.TextMid)
        SecondaryButton(stringResource(R.string.view_investigation), onOpen)
    }
}
