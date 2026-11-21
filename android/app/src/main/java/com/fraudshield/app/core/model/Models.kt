package com.fraudshield.app.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.Transient
import kotlinx.serialization.json.JsonObject

@Serializable
enum class Verdict { VERIFIED, SAFE, CAUTION, HIGH_RISK, CONFIRMED_FRAUD }

@Serializable
enum class AgentStatus { OK, LOW, SUSPICIOUS, HIGH }

@Serializable
enum class Agent { Message, Call, Link, Behavior }

@Serializable
enum class SignalType {
    @SerialName("sms") SMS,
    @SerialName("call") CALL,
    @SerialName("url") URL,
    @SerialName("qr") QR,
    @SerialName("screenshot") SCREENSHOT;

    val wireValue: String get() = name.lowercase()
}

@Serializable
enum class ActionType { CALL_1930, FREEZE_BANK, REPORT_NCRP, BLOCK_SENDER, SHARE_WARNING, NONE }

@Serializable
data class CaseAction(val type: ActionType, val label: String)

@Serializable
data class AgentFinding(
    val agent: Agent,
    val status: AgentStatus,
    val detail: String,
    val signals: List<String> = emptyList(),
)

@Serializable
data class Entities(
    val urls: List<String> = emptyList(),
    val phones: List<String> = emptyList(),
    @SerialName("otp_request") val otpRequest: Boolean = false,
)

@Serializable
data class Investigation(
    @SerialName("case_id") val caseId: String,
    val verdict: Verdict,
    @SerialName("risk_score") val riskScore: Int,
    val confidence: Double,
    @SerialName("agent_findings") val agentFindings: List<AgentFinding> = emptyList(),
    val reasons: List<String> = emptyList(),
    val entities: Entities = Entities(),
    val actions: List<CaseAction> = emptyList(),
    // Optional until the teammate confirms the history and full-case schemas.
    val type: SignalType? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @Transient val localMetadata: LocalCaseMetadata? = null,
) {
    init {
        require(riskScore in 0..100) { "Invalid backend risk_score" }
        require(confidence in 0.0..1.0) { "Invalid backend confidence" }
        require(caseId.isNotBlank()) { "Missing case_id" }
    }
}

@Serializable
data class AnalyzeRequest(
    val type: SignalType,
    val payload: JsonObject,
    val locale: String,
    @SerialName("client_ts") val clientTs: String,
    @Transient val backgroundPermission: ProtectionPermission? = null,
    @Transient val sourcePackage: String? = null,
)

@Serializable
data class DeviceRegistration(@SerialName("device_token") val deviceToken: String)

@Serializable
data class HistoryPage(
    val items: List<Investigation>,
    @SerialName("next_cursor") val nextCursor: String? = null,
)

@Serializable
data class ReportRequest(
    @SerialName("case_id") val caseId: String? = null,
    val type: String,
    @SerialName("evidence_refs") val evidenceRefs: List<String>,
    val note: String? = null,
)

@Serializable
data class ReportReceipt(@SerialName("report_id") val reportId: String, val status: String)

@Serializable
data class GraphNode(val id: String, val label: String, val kind: String)

@Serializable
data class GraphEdge(val from: String, val to: String, val rel: String)

@Serializable
data class InvestigationGraph(val nodes: List<GraphNode>, val edges: List<GraphEdge>)

@Serializable
data class AssistantRequest(val question: String, @SerialName("case_id") val caseId: String? = null)

@Serializable
data class AssistantAnswer(val answer: String, val actions: List<CaseAction>, val disclaimer: String)

@Serializable
data class CountEntry(val label: String, val count: Int)

@Serializable
data class WeeklyEntry(val day: String, val count: Int)

@Serializable
data class VectorEntry(val label: String, val pct: Double)

@Serializable
data class Trends(
    @SerialName("total_scanned") val totalScanned: Int,
    @SerialName("threats_blocked") val threatsBlocked: Int,
    val categories: List<CountEntry>,
    val weekly: List<WeeklyEntry>,
    @SerialName("top_vectors") val topVectors: List<VectorEntry>,
)

@Serializable
data class FamilyAlertRequest(
    @SerialName("member_ids") val memberIds: List<String>,
    @SerialName("case_id") val caseId: String,
    val redacted: Boolean = true,
)

@Serializable
data class FamilyAlertReceipt(val sent: List<String>, val failed: List<String>)

@Serializable
data class Health(val status: String, @SerialName("model_versions") val modelVersions: Map<String, String>)

@Serializable
data class ApiError(val code: String, val message: String, val retryable: Boolean)

@Serializable
data class ApiErrorEnvelope(val error: ApiError)

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data object Empty : UiState<Nothing>
    data class Data<T>(val value: T) : UiState<T>
    data class Error(val message: String, val retryable: Boolean = true, val code: String? = null) : UiState<Nothing>
}

data class FeaturePreview(val title: String, val description: String, val items: List<String>)
