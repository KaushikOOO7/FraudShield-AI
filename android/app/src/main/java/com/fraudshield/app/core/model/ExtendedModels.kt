package com.fraudshield.app.core.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable data class EvidenceReceipt(@SerialName("evidence_ref") val evidenceRef: String, @SerialName("expires_at") val expiresAt: String? = null)
@Serializable data class FamilyMember(val localId: String, val name: String, val phone: String? = null,
    val memberId: String? = null, val shareAlerts: Boolean = false, val consent: Boolean = false)
data class DataCounts(val cases: Int, val queuedReports: Int, val settings: Int)
data class ReportSubmission(val receipt: ReportReceipt? = null, val queuedId: String? = null)
